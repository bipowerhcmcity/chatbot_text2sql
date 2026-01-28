from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_community.document_loaders.csv_loader import CSVLoader

api_key = "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"

file_path = "data/event_description.csv"
loader = CSVLoader(file_path=file_path,encoding="utf-8")
documents = loader.load() # Each row becomes a Document object

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-large",
    api_key=api_key
)

# Create new embedings 
vectorstore = Chroma.from_documents(
    collection_name="event_description",
    documents=documents,
    embedding=embeddings,
    persist_directory="chroma_db"
)
