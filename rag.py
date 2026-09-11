from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    Docx2txtLoader
)

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_chroma import Chroma


# -------------------------
# Embedding Model
# -------------------------

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

embeddings = HuggingFaceEmbeddings(
    model_name=EMBEDDING_MODEL
)


# -------------------------
# Vector Database
# -------------------------

VECTOR_DB_PATH = "chroma_db"


# -------------------------
# Load Documents
# -------------------------

def load_document(file_path):

    if file_path.endswith(".pdf"):
        loader = PyPDFLoader(file_path)

    elif file_path.endswith(".txt"):
        loader = TextLoader(
            file_path,
            encoding="utf-8"
        )

    elif file_path.endswith(".docx"):
        loader = Docx2txtLoader(file_path)

    else:
        raise ValueError("Unsupported file type")

    return loader.load()


# -------------------------
# Split Documents
# -------------------------

def split_documents(documents):

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )

    return splitter.split_documents(documents)


# -------------------------
# Create Vector Database
# -------------------------

def create_vector_database(documents):

    chunks = split_documents(documents)

    vector_db = Chroma(
        persist_directory=VECTOR_DB_PATH,
        embedding_function=embeddings
    )

    vector_db.add_documents(chunks)

    return vector_db