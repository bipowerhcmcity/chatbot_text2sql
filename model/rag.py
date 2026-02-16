from langchain_chroma import Chroma
import pandas as pd 

def get_retriever(embeddings,collection_name, message, embedding_dir="chroma_db",  num_results=10):
    vector_store = Chroma(
        collection_name=collection_name,
        persist_directory=embedding_dir,
        embedding_function=embeddings
    )
    retriever = vector_store.as_retriever(search_kwargs={'k': num_results})
    
    docs = retriever.invoke(message)
    knowledges = [doc.page_content for doc in docs]
    return knowledges

def event_screen_mapping(screen_knowledges, event_knowledges):
    # Read event_screen_metadata 
    screen_event_metadata = pd.read_csv("data/Event Metadata(Processed v1).csv")

    if screen_knowledges !=None:
        screen_df = pd.DataFrame(
            dict(line.split(": ", 1) for line in item.split("\n"))
            for item in screen_knowledges
        )
    else: 
        screen_df = screen_event_metadata.copy()

    if event_knowledges != None:
        event_df = pd.DataFrame(
            dict(line.split(": ", 1) for line in item.split("\n"))
            for item in event_knowledges
        )
    else: 
        event_df = screen_event_metadata.copy()

    screen_event_df = screen_df.merge(event_df, how="cross",suffixes=("", "_meta"))
    print("Raw", screen_event_df)

    screen_event_df = screen_event_df[["ctx_screen_location","ctx_event_name"]].merge(screen_event_metadata, on=["ctx_screen_location","ctx_event_name"], how="inner")
    print("Combination screen-event", screen_event_df)
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
        
        print("Screen finding: ",screen_knowledges)
        print("Event finding: ",event_knowledges)

        event_screen_df = event_screen_mapping(screen_knowledges, event_knowledges)
        event_screen_prompts = event_screen_df.apply(row_to_prompt, axis=1).tolist()
        print(event_screen_prompts)
        return event_screen_prompts