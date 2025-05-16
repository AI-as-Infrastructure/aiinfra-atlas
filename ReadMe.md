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

1. Clone the repository
2. Rename .env.template to .env.development and update the settings (note LLM API Keys, or Ollama endpoint).
3. Start the development server (dependencies will be installed automatically):

   ```bash
   # Terminal 1 - Backend (FastAPI + ChromaDB)
   make db

   # Terminal 2 - Frontend (Vue + Vite)
   make df
   ```
3. Access the frontend via http://localhost:5173
4. (Optional) To clean and reset your environment:
   ```bash
   make dd
   ```

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