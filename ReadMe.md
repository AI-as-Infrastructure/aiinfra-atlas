# ATLAS Project

## Overview
ATLAS: Analysis and Testing of Language Models for Archival Systems is a test harness for the evaluation of Large Language Model (LLM) Retrieval Augmented Generation (RAG) for Humanities & Social Science (HASS) research. ATLAS is a deliverable of the [AI as Infrastructure (AIINFRA)](https://aiinfra.anu.edu.au) project. AIINFRA's primary goal is to develop an evaluation framework for LLM RAG systems designed for historical research.

## Project Status
The project is under development and makes heavy use of AI coding support. 

## Environment Requirements

- **Python:** 3.10.x (required for backend and all scripts)
- **Node.js:** 22.14.0 (required for frontend; enforced via .nvmrc and package.json)


## Core Components
ATLAS is built using the following technologies:

- FastAPI
- Vue 3
- Vite
- Chroma DB
- LangChain
- OpenTelemetry
- Phoenix: (Optional) 

Other dependencies include: Python virtual environments (`venv`), NVM, Sentence Transformers for embeddings, and various optional LLM providers (OpenAI, Anthropic, Ollama, etc.).

## Quick Start

1. Clone the repository.
2. Install Git LFS and pull the default vector store:
   ```bash
   git lfs install
   git lfs pull
   ```
3. Rename .env.template to .env.development and update the settings.
4. Start the development server (dependencies will be installed automatically):

   ```bash
   # Terminal 1 - Backend (FastAPI + ChromaDB)
   make db

   # Terminal 2 - Frontend (Vue + Vite)
   make df
   ```
5. Access the frontend via http://localhost:5173
6. (Optional) To clean and reset your environment:
   ```bash
   make dd
   ```

### Default Vector Store Setup

ATLAS requires a vector store for semantic search. You have two options:

1. **Use Mean Pooling (Default)**
   - No additional setup required
   - Uses a simple but effective embedding strategy
   - Suitable for basic testing and development

2. **Generate Custom Vector Store**
   - Recommended for production use
   - Provides better semantic search capabilities
   - Run the following command:
   ```bash
   make store
   ```
   This will:
   - Generate embeddings using the BERT model
   - Create a vector store in `backend/targets/chroma_db/`
   - May take several minutes depending on your system

Note: The vector store generation process is optional but recommended for optimal performance. The default vector store included in the repository has been pre-generated using the create store process and includes fine-tuned embeddings. However, to use these fine-tuned embeddings, you'll need the corresponding fine-tuned model files in your models directory. If you don't have these files, the system will fall back to using mean pooling for embeddings.

### Vector Store & Retriever Generation Workflow

ATLAS provides a workflow for building new vector stores and generating compatible retrievers:

- The `create/` directory contains template scripts for generating vector stores (e.g., Hansard) and matching retriever classes.
- You can add new corpora (e.g., novels, newspapers) by copying and adapting these scripts.
- The following Makefile targets are available:

```bash
make store      # Builds the vector store using create/create_hansard_store.py
make retriever  # Generates a compatible retriever using create/create_hansard_retriever.py
```

Both targets will:
- Ensure the Python virtual environment is set up and dependencies are installed
- Use the unified project requirements.txt for consistency
- Output results to the `create/output/` directory

This workflow ensures that your retrievers are always in sync with your vector store schema and configuration. 

## License
- [License](LICENSE.md)