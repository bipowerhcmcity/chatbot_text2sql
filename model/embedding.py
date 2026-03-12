from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_community.document_loaders.csv_loader import CSVLoader
from langchain_core.documents import Document

import os
from dotenv import load_dotenv
import pandas as pd

from chromadb import PersistentClient

api_key = os.getenv("OPENAI_API_KEY")

def table_dataframe_to_doc(file_path):

    df = pd.read_csv(file_path)
    print(df)

    documents = []

    for _, row in df.iterrows():
        doc = Document(
            page_content=f"""
    Tên dữ liệu: {row['Tên dữ liệu']}
    Mô tả: {row['Mô tả']}
    Nhóm dữ liệu: {row['Nhóm dữ liệu']}
    """,
            metadata={
                "service": row["Dịch vụ"],
                "table_name": row["Tên dữ liệu"],
                "group": row["Nhóm dữ liệu"]
            }
        )
        documents.append(doc)
    return documents

def create_embedding_store(file_path, collection_name, out_directory, tbl_schema=True): 
    if tbl_schema:
        documents = table_dataframe_to_doc(file_path)
    else:
        loader = CSVLoader(file_path=file_path,encoding="utf-8")
        documents = loader.load() # Each row becomes a Document object

    client = PersistentClient(path=out_directory)
    try:
        client.delete_collection(name=collection_name)
    except:
        pass

    # Create new embedings 
    vectorstore = Chroma.from_documents(
        collection_name=collection_name,
        documents=documents,
        embedding=embeddings,
        persist_directory=out_directory
    )


embeddings = OpenAIEmbeddings(
    model="text-embedding-3-large",
    api_key=api_key
)

create_embedding_store(file_path="data/table_description_metadata.csv", collection_name="table_metadata", out_directory="chroma_db", tbl_schema=True)