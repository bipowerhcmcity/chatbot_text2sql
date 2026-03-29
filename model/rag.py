from langchain_chroma import Chroma
import pandas as pd 
import re
import json
from pathlib import Path

import inspect

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
    knowledges = [{"doc":result[0].page_content, "score":result[1] } for result in results]
    return knowledges

def get_all_table(embedding, entities, service, num_result=5):
    res_tbs = []
    for entity in entities:
        res_retrieve = get_retriever(embedding, collection_name="table_metadata",message=entity, num_results=num_result, service=service)
        print("Finding tables for entity:", entity, "Results:", res_retrieve)
        res_tb = [re.search(r"Tên dữ liệu:\s*(.*)", res["doc"]).group(1) for res in res_retrieve]
        res_tbs+=res_tb
    return res_tbs

def get_join_rules(table_name):
    """Return join rules dict for `table_name` from data/join_map.json.

    Returns None if no join rules found or on error. The returned dict has
    the shape: { 'table': table_name, 'joins': [ {from_table,to_table,left_column,right_column,score,reason}, ... ] }
    """
    join_map_path = Path("data") / "join_map.json"
    try:
        if not join_map_path.exists():
            return None
        jm = json.loads(join_map_path.read_text(encoding='utf-8'))
        key = table_name
        if key not in jm.get('joins', {}):
            key = table_name.lower()
        joins = jm.get('joins', {}).get(key, [])
        if not joins:
            return None

        def score_of(j):
            try:
                return float(j.get('score') or 0)
            except Exception:
                return 0

        joins_sorted = sorted(joins, key=score_of, reverse=True)
        join_items = []
        for j in joins_sorted:
            join_items.append({
                'from_table': table_name,
                'to_table': j.get('to_table'),
                'left_column': j.get('left_column'),
                'right_column': j.get('right_column'),
                'score': j.get('score'),
                'reason': j.get('reason')
            })
        return {'table': table_name, 'joins': join_items}
    except Exception:
        return None

def extract_table_prompt(table_name): 
    table_description = pd.read_csv("data/table_description_metadata.csv")
    schema_description = pd.read_csv("data/schema_metadata.csv")

    table_desc = table_description[table_description["Tên dữ liệu"]==table_name]
    table_schema = schema_description[schema_description["TableName"]==table_name][["ColumnName","DataType","ColumnDescription"]].to_string(index=False)
    table_prompt = f"""
    Table: {table_name} - {table_desc["Dịch vụ"].values[0]} - {table_desc["Nhóm dữ liệu"].values[0]}

    {table_desc["Mô tả"].values[0]}

    Schema: 
    {table_schema}
    """
    # Append join rules (all, sorted by score) using helper
    join_block = get_join_rules(table_name)
    if join_block:
        table_prompt = table_prompt + "\nJoin rules:\n"
        table_prompt = table_prompt + json.dumps(join_block, ensure_ascii=False, indent=2) + "\n"
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
 

def get_business_rules(service):
    """
    Load business rules for the given service from data/*_business_rules.txt (case-insensitive)
    and return a prompt-ready string. Returns an empty string if no rules found.
    """
    try:
        svc = (service or "").strip()
        if not svc:
            return ""

        svc_low = svc.lower()
        data_dir = Path("data/business_rules")
        if not data_dir.exists():
            return ""

        # Prefer exact "<service>_business_rules.*" matches (case-insensitive)
        candidates = []
        for p in data_dir.iterdir():
            name = p.name.lower()
            if name.endswith("_business_rules.txt") and name.startswith(f"{svc_low}_business_rules"):
                candidates.append(p)

        # Fallback: any file containing both service name and "_business_rules"
        if not candidates:
            for p in data_dir.iterdir():
                name = p.name.lower()
                if "_business_rules" in name and svc_low in name:
                    candidates.append(p)

        if not candidates:
            return ""

        # Read and concatenate candidate files (sorted for deterministic order)
        contents = []
        for p in sorted(candidates):
            try:
                txt = p.read_text(encoding="utf-8").strip()
                if txt:
                    contents.append(f"Source: {p.name}\n{txt}")
            except Exception:
                # Skip unreadable files
                continue

        if not contents:
            return ""

        prompt = (
            f"Business rules for service '{svc}':\n\n"
            + "\n\n---\n\n".join(contents)
            + "\n\nPlease follow these rules when generating queries or explanations."
        )
        return prompt
    except Exception:
        return ""