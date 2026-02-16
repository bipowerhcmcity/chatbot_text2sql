from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_community.document_loaders.csv_loader import CSVLoader
import os
from dotenv import load_dotenv

api_key = os.getenv("OPENAI_API_KEY")


def create_embedding_store(file_path, collection_name, out_directory): 
    loader = CSVLoader(file_path=file_path,encoding="utf-8")
    documents = loader.load() # Each row becomes a Document object

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

create_embedding_store(file_path="data/screen_location_metadata.csv", collection_name="screen_metadata", out_directory="chroma_db")
create_embedding_store(file_path="data/event_metadata.csv", collection_name="event_metadata", out_directory="chroma_db")
