# ATLAS Project

## Overview
This is a test harness for the evaluation of Large Language Model (LLM) Retrieval Augmented Generation (RAG) for Humanities & Social Science (HASS) research. ATLAS is a deliverable of the [AI as Infrastructure (AIINFRA)](https://aiinfra.edu.au) project. AIINFRA's primary goal is to develop an evaluation framework for LLM RAG systems designed for historical research.

## Quick Start

> **Important:** This version of ATLAS uses the AWS Cognito service for authentication, to protect user data and limit inferencing costs.  Be sure to set your Cognito settings along with other .env settings. You must set up an AWS Cognito User Pool and configure the appropriate settings in your `.secrets` file for the application to work properly. AWS Cognito was chosen because of its support for a broad range of email and SMS authentication methods.

### 1. Set Up Configuration Files
```bash
# Install Git LFS (if not already installed)
# Ubuntu/Debian
sudo apt-get install git-lfs
# macOS
brew install git-lfs

# Clone the repository with LFS support
git clone https://github.com/AI-as-Infrastructure/aiinfra-atlas
cd aiinfra-atlas
git lfs pull  # Pull Redis data dump and other large files

# Create configuration files from templates
cp config/.env.template config/.env
cp config/.secrets.template config/.secrets
```

> **Note:** Git LFS is required to download the Redis data dump files which contain the vector database for the RAG system.

### 2. Configure Your Environment
```bash
# Edit .env to set your environment (dev, staging, or prod)
# The ENVIRONMENT variable controls which settings are used
nano config/.env

# Add your API keys and AWS Cognito settings to .secrets
nano config/.secrets
```

### 3. Start the Application
```bash
# For development environment
make dev

# In a separate terminal, start the frontend
make frontend
```

### 4. Switch Environments
To switch between environments, use:
```bash
# Development environment
make dev

# Staging environment
make staging

# Production environment
make prod
```

## Development
ATLAS is intended for research use only. We acknowledge the labour put into the code used for LLM training, and the environmental impact of the development process. This impact will be factored into the project's final report.

## Purpose
ATLAS (Analysis and Testing of Language Models for Archival Systems) enables reproducible and transparent experiments with multiple models and is built using principles of responsible and slow AI. The tool was designed with scholarly and Indigenous values in mind, providing detailed technical information about the 'calibration' of each experiment (model version, word embedding, vector store characteristics, system prompt), as well as the source documents used by the foundation model to generate its response.

Details of cost per prompt and observability of code functions are supported through a connected cloud platform. Transparency and alignment to Humanities & Social Science (HASS) and Galleries, Libraries, Archives & Museums (GLAM) standards (FAIR, CARE) is facilitated in the default production app (not publicly available for ethical reasons) using a baseline transnational corpus comprising Hansard debates from 1901 in Australia, Aotearoa New Zealand, and the United Kingdom.

Indigenous and Māori data sovereignty principles and ethics inform the tool's technical design as well as an associated evaluation framework. Historical word embeddings ensure the corpus vector store (database) aligns to the historical semantics of 1901. The Hansard sources were chosen as a nod to Australian Federation, but also to provide a transnational corpus capable of testing the ability of LLM systems to respond appropriately to challenging content loaded with cultural and post-colonial meaning.

## Telemetry
ATLAS collects anonymous usage data to help improve the application and understand research patterns. This telemetry includes:

- Tracking of RAG 'traces', which allows analysis of the query process and model responses.
- Model response quality feedback, for answers and citations.

Telemetry data is collected with privacy and data sovereignty principles in mind, aligning with the project's commitment to responsible AI practices. All collected data is anonymized and aggregated before analysis. this improves observability and evaluation. 

A Phoenix Arize API key is required to enable telemetry functionality. Without this API key, telemetry collection will not be active. [Phoenix Arize](https://www.phoenixarize.com/) is a commercial observability platform, with free tier available, that provides a user-friendly interface for monitoring and analyzing telemetry data. ATLAS uses [Open Telemetry](https://opentelemetry.io/) for maximum portability to alternative platforms.

## Service Configuration

ATLAS requires several API keys to be configured in the `.secrets` file for full functionality:

- **OpenAI API Key**: Required for OpenAI language models (GPT-3.5, GPT-4, etc.)
- **Anthropic API Key**: Required for Anthropic models (Claude, etc.)
- **Phoenix Arize API Key**: Required for telemetry and observability features
- **AWS Cognito Settings**: Required for authentication (as mentioned in the Authentication section)
- **Ollama Endpoint**: Required for Ollama models (as mentioned in the Authentication section). Can be hosted locally or through an online service.

### Setting Up API Keys

1. Copy the template file to create your secrets file:
   ```bash
   cp config/.secrets.template config/.secrets
   ```

2. Edit the `.secrets` file to add your API keys:
   ```bash
   nano config/.secrets
   ```
   Replace `<DEFAULT>` values with your actual API keys:
   ```
   OPENAI_API_KEY="your_openai_api_key_here"
   ANTHROPIC_API_KEY="your_anthropic_api_key_here"
   PHOENIX_API_KEY="your_phoenix_api_key_here"
   ```

3. The application will automatically load and use these API keys when you run it.

**Note**: The `.secrets` file should never be committed to version control. It is already in `.gitignore` to prevent accidental commits.

If you don't have valid API keys for all services, the application will still run but with limited functionality. You'll see warnings during startup about missing or default API keys. You can add more API keys to the `.secrets` file to enable additional services, using  ```<NEW_KEY>_API_KEY="your_new_api_key_here"```. Note that LLMs have different characteristics and may require changes to the system prompt to smooth out unexpected or unwanted behavior.

## Test Target Configuration

ATLAS uses configurable test targets to define LLM models, vector stores, and other related settings for experiments:

- Test targets are defined in the `backend/targets/` directory
- `blert_500.py` is the default test target and can be used as a template for creating new ones
- The active test target is configured via the `TEST_TARGET` environment variable

Each test target defines:

- **LLM Models**: Configuration for OpenAI, Anthropic, and Ollama models
- **Embedding Models**: Which embedding model to use for vector search
- **Search Parameters**: Threshold settings, k-values, and other retrieval parameters
- **Prompt Templates**: System prompts and other template configurations

To create a new test target, copy and modify the `blert_500.py` file with your desired configurations. Test targets enable reproducible experiments with different models and parameters.

### Vector Store Creation

ATLAS includes a default vector store of Hansard debates from Australia, Aotearoa New Zealand, and the United Kingdom from 1901. New vector stores can be created using the companion repository:

[https://github.com/AI-as-Infrastructure/aiinfra-create-store](https://github.com/AI-as-Infrastructure/aiinfra-create-store)

This repository allows you to:
- Use different source documents
- Apply different word embeddings (including historical embeddings)
- Extract custom metadata from source documents
- Configure vector store parameters

**Important Note**: If you make significant architectural changes to the vector store (beyond just changing source texts), you may need to modify `retriever.py` to accommodate these changes.

## Development Environment

### System Requirements and Compatibility

This project was developed and tested with the following environment:

- **Operating System**: Pop_OS! (Ubuntu-based)
- **Python Version**: 3.10.12
- **Node.js Version**: 20.11.1
- **Hardware**: NVIDIA GPU support

While the application may work with other systems and Python/Node.js versions (Python 3.11/3.12, Node 18/21), the above configuration is recommended for maximum compatibility and consistent behavior. The requirements.lock file includes platform-specific dependencies that may not work on different systems, especially those without NVIDIA GPU support.

**Important**: The project uses the `PYTHON_VERSION` and `NODE_VERSION` environment variables (set in `.env`) to determine which versions to use for creating the development environment. These should be set to match your installed versions (defaults are Python 3.10 and Node.js 20.11.1).

**Additional Linux Dependency for Audio Support**:

Recent versions of some dependencies (notably those related to OpenAI) require that the PortAudio library is installed. You can install it via:

```bash
sudo apt-get update
sudo apt-get install portaudio19-dev
```

### Setting Up Development Environment

1. **Check your Python version**:
   ```bash
   make check-env
   ```
   This will show your current Python version and provide guidance if it doesn't match the recommended version.

2. **Setup the development environment**:
   ```bash
   make dev
   ```
   This will:
   - Create a virtual environment using Python 3.10.12 (or your configured version)
   - Install dependencies (preferably from requirements.lock)
   - Set up Redis and Nginx in Docker containers
   - Launch the Flask backend application

3. **Start the frontend** (in a separate terminal):
   ```bash
   make frontend
   ```
   This will:
   - Install Node.js dependencies using npm
   - Start the React development server on port 3001
   - Connect to the backend through the Nginx proxy

4. **Dependency Management**:
   - The project uses requirements.lock for reproducible environments
   - If you need to generate a new lock file for your specific environment:
     ```bash
     make lock
     ```
   - Note: Lock files are machine-specific and might not work across different environments

5. **Cleanup**:
   ```bash
   make destroy-dev
   ```
   This will remove all development containers, virtual environments, and temporary files.

### Troubleshooting Common Issues

- **Python Version Errors**: Ensure you have Python 3.10 installed and set `PYTHON_VERSION="3.10"` in `.env`
- **Node.js Version Issues**: Ensure you have Node.js 20.11.1 installed and set `NODE_VERSION="20.11.1"` in `.env`
- **Dependency Conflicts**: Try running `make dev --clean` to rebuild the virtual environment
- **SSL Certificate Errors**: Check that your SSL certificates are correctly configured in `.env`
- **Redis Connection Issues**: Ensure Redis is running properly with `docker ps | grep redis-dev`
- **Nginx Connection Issues**: Verify Nginx configuration with `docker logs nginx-dev`

