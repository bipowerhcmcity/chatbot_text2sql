from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_community.document_loaders.csv_loader import CSVLoader
import os
from dotenv import load_dotenv

api_key = os.getenv("OPENAI_API_KEY")

file_path = "data/item_metadata.csv"
loader = CSVLoader(file_path=file_path,encoding="utf-8")
documents = loader.load() # Each row becomes a Document object

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-large",
    api_key=api_key
)

# Create new embedings 
vectorstore = Chroma.from_documents(
    collection_name="item_metadata",
    documents=documents,
    embedding=embeddings,
    persist_directory="chroma_db"
)
