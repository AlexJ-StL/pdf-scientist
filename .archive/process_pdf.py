import PyPDF2
import os
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.llms import OpenAI
import tiktoken
import pandas as pd
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

# Replace with your actual API keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MONGODB_URI = os.getenv("MONGODB_URI")

def process_pdf(pdf_path_or_url, filename):
    # Determine if it's a local file or URL
    if os.path.exists(pdf_path_or_url):
        pdf_reader = PyPDF2.PdfReader(open(pdf_path_or_url, "rb"))
    else:
        # Add code here to download PDF from URL
        # For example, using requests library
        pass  # Replace with URL handling logic

    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()

    # Initialize text splitter and embeddings
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500, chunk_overlap=100, length_function=tiktoken.count_tokens
    )
    embeddings = OpenAIEmbeddings()

    # Split text into chunks
    chunks = text_splitter.split_text(text)

    # Connect to MongoDB
    client = MongoClient(MONGODB_URI)
    db = client["epa_methods"]  # Replace with your desired database name
    collection = db["documents"]

    # Store chunks in MongoDB
    for i, chunk in enumerate(chunks):
        embedding = embeddings.embed_query(chunk)
        document = {
            "filename": filename,
            "chunk_index": i,
            "text": chunk,
            "embedding": embedding,
        }
        collection.insert_one(document)

    # Log processing event
    log_data = {
        "PDF Title": filename,
        "Processing Date and Time": pd.Timestamp.now(),
        "Number of Chunks Created": len(chunks),
        "Number of Tokens in Processed Data": tiktoken.count_tokens(text),
    }
    log_df = pd.DataFrame([log_data])
    log_df.to_csv("processing_log.csv", mode="a", header=False, index=False)

    client.close()

    return collection

# Example usage (replace with your PDF path or URL)
# collection = process_pdf("path/to/your/pdf.pdf", "your_pdf_filename")
# Or for URL:
# collection = process_pdf("https://www.example.com/your_pdf.pdf", "your_pdf_filename")

