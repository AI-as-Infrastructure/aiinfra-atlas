import os
import importlib
import logging

# Import secrets manager to access configuration
from utils.secrets_manager import get_secret

# Import LLM providers
from langchain_community.chat_models import ChatOllama
from langchain_openai.chat_models.base import ChatOpenAI
from langchain_anthropic.chat_models import ChatAnthropic
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.vectorstores import Redis
from langchain_core.runnables import RunnablePassthrough
from langchain_huggingface import HuggingFaceEmbeddings  
import logging

# ---- LOGGING CONFIG ----
logging.basicConfig(level=logging.DEBUG)

# Load the target configuration module name from the environment.
# This is self-referential in this file, but kept for consistency with other modules
target_config_name = os.getenv('TEST_TARGET')
if not target_config_name:
    raise ValueError("TEST_TARGET environment variable not set.")
# No need to import self

# ---- LOAD CONFIGURATION USING SECRETS MANAGER ----
REDIS_PASSWORD = get_secret("REDIS_PASSWORD")
if not REDIS_PASSWORD:
    raise ValueError("REDIS_PASSWORD not found in configuration")

# Construct Redis URL with password
REDIS_HOST = get_secret("REDIS_HOST", "localhost")
REDIS_PORT = get_secret("REDIS_PORT", "6379")
REDIS_URL = f"redis://default:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}"

# ---- TEST TARGET CONFIGURATION ----
# Each test target defines an LLM, vector store, and other related settings.

# LLM Configuration
# Get OLLAMA_ENDPOINT from configuration with fallback to default Docker host
OLLAMA_ENDPOINT = get_secret("OLLAMA_ENDPOINT", "http://host.docker.internal:11434")
logging.info(f"Using Ollama endpoint: {OLLAMA_ENDPOINT}")
OLLAMA = ChatOllama(model="llama3.2", base_url=OLLAMA_ENDPOINT, streaming=True)

# Initialize API clients with keys from secrets manager
OPENAI_API_KEY = get_secret("OPENAI_API_KEY")
OPENAI = ChatOpenAI(
    api_key=OPENAI_API_KEY,
    model_name="gpt-4o-mini", 
    temperature=0, 
    streaming=True
)

ANTHROPIC_API_KEY = get_secret("ANTHROPIC_API_KEY")
ANTHROPIC = ChatAnthropic(
    api_key=ANTHROPIC_API_KEY,
    model_name="claude-3-5-sonnet-20240620", 
    streaming=True
)

# Define the selected test target 
LLM = ANTHROPIC  # Default test target 
EMBEDDING_MODEL = 'Livingwithmachines/bert_1890_1900'
SEARCH_TYPE = 'similarity_score_threshold'
SEARCH_KWARGS = {
    "k": 15,                  # For Redis compatibility - this is fetch_k
    "score_threshold": 0.0,
    "citation_limit": 10      # Number of citations to show
}

# Vector Store Configuration
VECTOR_STORE = Redis
# Use the complete connection string read from the environment.
DATABASE_URL = REDIS_URL
INDEX_NAME = 'lwm_bert_1890_1900_v.1.0'
ALGORITHM = 'FLAT'
CHUNK_SIZE = '500'
CHUNK_OVERLAP = '75'

# Index Schema (Defines metadata fields used in Redis)
index_schema = {
    "text": [
        {"name": "id"},  # Ensure ID is included
        {"name": "content"},
        {"name": "source"},
        {"name": "date"},
        {"name": "url"},
        {"name": "page"},
        {"name": "loc"},
        {"name": "corpus"},
    ]
}

# ---- FORMAT DOCUMENTS ----
def format_docs(docs):
    """Formats retrieved documents with metadata for structured output."""
    formatted_docs = []
    for doc in docs:
        metadata = doc.metadata
        formatted_doc = {
            "id": metadata.get("id", "unknown"),
            "content": doc.page_content,
            "source": metadata.get("source", "unknown"),
            "date": metadata.get("date", "unknown"),
            "url": metadata.get("url", "unknown"),
            "loc": metadata.get("loc", "unknown"),
            "page": metadata.get("page", "unknown"),
        }
        formatted_docs.append(formatted_doc)
    return formatted_docs

# ---- RETRIEVER FUNCTION ----
def get_retriever():
    """Retrieve and initialize the vector store on demand, using the selected test target."""
    embedding = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

    vectorstore = VECTOR_STORE(
        redis_url=DATABASE_URL,
        index_name=INDEX_NAME,
        embedding=embedding,
        vector_schema={"algorithm": ALGORITHM},
        index_schema=index_schema,
    )

    # Filter out non-Redis parameters from search_kwargs
    redis_search_kwargs = {k: v for k, v in SEARCH_KWARGS.items() 
                          if k not in ["citation_limit"]}
    
    return vectorstore.as_retriever(search_type=SEARCH_TYPE, search_kwargs=redis_search_kwargs)

# ---- EXPORTS ----
__all__ = [
    'LLM', 'EMBEDDING_MODEL', 'DATABASE_URL', 'SEARCH_TYPE',
    'SEARCH_KWARGS', 'INDEX_NAME', 'ALGORITHM', 'CHUNK_SIZE', 'CHUNK_OVERLAP',
    'index_schema', 'format_docs', 'get_retriever'
]
