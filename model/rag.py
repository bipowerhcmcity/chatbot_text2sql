from langchain_chroma import Chroma
import pandas as pd 
import re

def get_retriever(embeddings,collection_name, message, service=None, embedding_dir="chroma_db",  num_results=10):
    vector_store = Chroma(
        collection_name=collection_name,
        persist_directory=embedding_dir,
        embedding_function=embeddings
    )
    if service == None:
        results = vector_store.similarity_search_with_score(message, k=num_results)
    else:
        results = vector_store.similarity_search_with_score(message, k=num_results, filter={"service":service})
        print(results)
    knowledges = [{"doc":result[0].page_content, "score":result[1] } for result in results]
    return knowledges

def get_all_table(embedding, entities, service):
    res_tbs = []
    for entity in entities:
        res_retrieve = get_retriever(embedding, collection_name="table_metadata",message=entity, num_results=5, service=service)
        res_tb = [re.search(r"Tên dữ liệu:\s*(.*)", res["doc"]).group(1) for res in res_retrieve]
        res_tbs+=res_tb
    return res_tbs

def extract_table_prompt(table_name): 
    table_description = pd.read_csv("data/table_description_metadata.csv")
    schema_description = pd.read_csv("data/schema_metadata.csv")

    table_desc = table_description[table_description["Tên dữ liệu"]==table_name]
    table_schema = schema_description[schema_description["TableName"]==table_name]
    table_prompt = f"""
    Table: {table_name} - {table_desc["Dịch vụ"].values[0]} - {table_desc["Nhóm dữ liệu"].values[0]}

    {table_desc["Mô tả"].values[0]}

    Schema: 
    {table_schema}
    """
    return table_prompt

def event_screen_mapping(screen_knowledges, event_knowledges):
    # Read event_screen_metadata 
    screen_event_metadata = pd.read_csv("data/Event Metadata(Processed v1).csv")

    if screen_knowledges !=None:
        screen_df = pd.DataFrame(
            dict(line.split(": ", 1) for line in item["doc"].split("\n"))
            for item in screen_knowledges
        )
        screen_df["screen_score"] = [item["score"] for item in screen_knowledges]
    else: 
        screen_df = screen_event_metadata.copy()[["ctx_screen_location","Screen Description"]]
        screen_df["screen_score"] = 1

    if event_knowledges != None:
        event_df = pd.DataFrame(
            dict(line.split(": ", 1) for line in item["doc"].split("\n"))
            for item in event_knowledges
        )
        event_df["event_score"] = [item["score"] for item in event_knowledges]
    else: 
        event_df = screen_event_metadata.copy()[["ctx_event_name","Event Description"]]
        event_df["event_score"] = 1

    screen_event_df = screen_df.merge(event_df, how="cross")
    screen_event_df["total_score"] = screen_event_df["event_score"] * screen_event_df["screen_score"] 

    screen_event_df = screen_event_df[["ctx_screen_location","ctx_event_name","total_score"]].merge(screen_event_metadata, on=["ctx_screen_location","ctx_event_name"], how="inner").sort_values(by="total_score").drop_duplicates()
    return screen_event_df.head(10)

def row_to_prompt(row):
    return "\n".join(f"{col}: {row[col]}" for col in row.index)

def get_event_screen_knowledge(structure_dict, embeddings): 
    # Step 2: RAG: 
    knowledges = ""
    #step 2.1 RAG event description 
    if structure_dict["event_context"]!= None:
        event_context = structure_dict["event_context"]
        if event_context["screen_description"] == None: 
            screen_knowledges = None
        else:
            screen_knowledges = get_retriever(embeddings, collection_name="screen_metadata", message=event_context["screen_description"], num_results=10)
        
        if event_context["action_description"] == None: 
            event_knowledges = None
        else:
            event_knowledges = get_retriever(embeddings, collection_name="event_metadata", message=event_context["action_description"], num_results=10)

        event_screen_df = event_screen_mapping(screen_knowledges, event_knowledges)
        event_screen_prompts = event_screen_df.apply(row_to_prompt, axis=1).tolist()
        return event_screen_prompts