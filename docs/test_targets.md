# ATLAS Test Targets

Test targets are the core configuration system that defines how ATLAS processes queries and retrieves documents. Each test target combines an LLM configuration with search parameters to create a complete question-answering pipeline.

## Overview

A test target consists of three complementary components:

1. **Test Target Configuration** (e.g., `k15_claude37.txt`) - Defines LLM provider, model, and search parameters
2. **Vector Store Manifest** (e.g., `blert_1000.txt`) - Records vector store creation metadata and statistics  
3. **Retriever Implementation** - Connects the target configuration to the vector store for document retrieval

These components work together to create a complete retrieval-augmented generation (RAG) system.

## Test Target Configuration Files

Test target configuration files are located in `backend/targets/` and follow the naming pattern `{target_name}.txt`. They define the LLM and search parameters for a specific configuration.

### Configuration Structure

```ini
# K15 Claude 3.7 Test Target Configuration

# LLM Configuration
LLM_PROVIDER=ANTHROPIC
LLM_MODEL=claude-3-7-sonnet-20250219

# Search-K (fetch-k) controls the number of document chunks sent to the LLM for analysis
SEARCH_K=15
# Citation limit only controls the number of citations displayed in the UI
CITATION_LIMIT=15
SEARCH_SCORE_THRESHOLD=0.0

# Target Information
TARGET_VERSION=1.0
```

### Key Parameters

#### LLM Configuration
- **`LLM_PROVIDER`**: The LLM provider (`ANTHROPIC`, `OPENAI`, `GOOGLE`, `BEDROCK`, `OLLAMA`)
- **`LLM_MODEL`**: The specific model to use (e.g., `claude-3-7-sonnet-20250219`, `gpt-4o`, `gemini-2.0-flash`)

#### Search Parameters
- **`SEARCH_K`**: Number of document chunks retrieved and sent to the LLM for analysis (fetch-k)
- **`CITATION_LIMIT`**: Maximum number of citations displayed in the UI (does not affect retrieval)
- **`SEARCH_SCORE_THRESHOLD`**: Minimum similarity score for retrieved documents (usually 0.0)

#### Metadata
- **`TARGET_VERSION`**: Configuration version for tracking changes

## Vector Store Manifest Files

Vector store manifest files record the creation metadata and statistics for each vector store. They share the same basename as the `CHROMA_COLLECTION_NAME` and provide essential information about the underlying data.

### Manifest Structure

```
Vector Store Creation Statistics
=====================================

Collection: blert_1000
Created: 2025-07-11 11:38:26

Model Information
---------------
Model: Livingwithmachines/bert_1890_1900
Embedding Dimension: 768
Quantized: False
Model Hash: None

Processing Configuration
----------------------
Text Splitter: RecursiveCharacterTextSplitter
Chunk Size: 1000
Chunk Overlap: 100
Batch Size: 100

Corpus Statistics
---------------
1901_au:
  Files: 113
  Chunks: 40,756
  Characters: 27,954,688
  Words: 4,679,284

1901_nz:
  Files: 62
  Chunks: 23,503
  Characters: 22,033,368
  Words: 4,019,262

1901_uk:
  Files: 31
  Chunks: 30,677
  Characters: 23,815,338
  Words: 4,040,154

Total Corpus Statistics
---------------------
Total Files: 206
Total Chunks: 94,936
Total Characters: 73,803,394
Total Words: 12,738,700
```

### Key Information

#### Model Configuration
- **Embedding Model**: Which model was used to create embeddings
- **Embedding Dimension**: Vector dimensionality (768 for BERT-based models)
- **Processing Configuration**: Chunking strategy and parameters

#### Corpus Composition
- **Per-Corpus Statistics**: Files, chunks, and content size for each corpus
- **Total Statistics**: Overall collection size and composition
- **Corpus Distribution**: Percentage breakdown of content by corpus

## How Test Targets Work

### 1. Target Selection

The active test target is set via the `TEST_TARGET` environment variable:

```bash
# In .env.development
TEST_TARGET=k15_claude37
```

### 2. Configuration Loading

The `TargetConfig` class in `base_target.py` loads configuration from multiple sources:

1. **Environment variables** - Core settings like `TEST_TARGET`, `CHROMA_COLLECTION_NAME`
2. **Test target file** - LLM and search parameters from `{TEST_TARGET}.txt`
3. **Vector store manifest** - Metadata from `{CHROMA_COLLECTION_NAME}.txt`

### 3. Composite Target Creation

ATLAS creates a composite target identifier combining the test target and vector store:

```
Composite Target = {TEST_TARGET}_{CHROMA_COLLECTION_NAME}
Example: k15_claude37_blert_1000
```

This ensures the exact combination of configuration and data is tracked for reproducibility.

### 4. Query Processing Pipeline

When a user submits a question:

1. **Document Retrieval**: Vector store retrieves `SEARCH_K` most relevant chunks
2. **Corpus Filtering**: Applies corpus filter if specified (e.g., `1901_au`)
3. **LLM Processing**: Sends chunks to configured LLM for answer generation
4. **Citation Generation**: Returns up to `CITATION_LIMIT` source citations

## Available Test Targets

ATLAS includes several pre-configured test targets:

### Memory-Optimized Targets
- **`k15_claude37`**: Claude 3.7 with 15-chunk retrieval
- **`k20_google_gemini_2.0`**: Gemini 2.0 with 20-chunk retrieval (memory optimized)
- **`k15_openai4o`**: OpenAI GPT-4o with 15-chunk retrieval

### Higher-Capacity Targets  
- **`k30_claude4`**: Claude 4 with 30-chunk retrieval
- **`k30_google_gemini_2.0`**: Gemini 2.0 with 30-chunk retrieval

### Cloud Provider Targets
- **`k15_bedrock_claude3`**: AWS Bedrock Claude 3 with 15-chunk retrieval

### Target Naming Convention

Test targets follow the pattern: `k{SEARCH_K}_{provider}_{model_version}`

- **k15**: Retrieves 15 document chunks
- **claude37**: Uses Claude 3.7 Sonnet
- **google_gemini_2.0**: Uses Google Gemini 2.0 Flash

## Relationship to Vector Stores and Retrievers

Test targets work in conjunction with vector stores and retrievers as documented in [create_store.md](create_store.md):

### Vector Store Foundation
- **Vector Store**: Contains the embedded document chunks and metadata
- **Manifest File**: Records creation parameters and corpus statistics
- **Embedding Model**: Must match between store creation and retrieval

### Retriever Integration
- **HansardRetriever**: Implements the retrieval logic using the vector store
- **Search Configuration**: Uses test target parameters for retrieval behavior
- **Corpus Filtering**: Leverages metadata tags from vector store

### Configuration Harmony
All three components must be aligned:

```bash
# Environment configuration
TEST_TARGET=k15_claude37           # Defines LLM and search params
CHROMA_COLLECTION_NAME=blert_1000  # Defines vector store
RETRIEVER_MODULE=hansard_retriever # Defines retrieval implementation
EMBEDDING_MODEL=Livingwithmachines/bert_1890_1900  # Must match vector store
```

## Creating Custom Test Targets

### 1. Create Target Configuration

Create a new file in `backend/targets/`:

```ini
# K25 OpenAI GPT-4 Test Target Configuration

# LLM Configuration  
LLM_PROVIDER=OPENAI
LLM_MODEL=gpt-4o-mini

# Search Configuration
SEARCH_K=25
CITATION_LIMIT=20
SEARCH_SCORE_THRESHOLD=0.0

# Target Information
TARGET_VERSION=1.0
```

### 2. Update Environment Configuration

Set the new target in your environment file:

```bash
# In .env.development
TEST_TARGET=k25_openai_gpt4_mini
```

### 3. Verify Vector Store Compatibility

Ensure your vector store manifest exists and is compatible:
- Check `backend/targets/{CHROMA_COLLECTION_NAME}.txt` exists
- Verify embedding model compatibility
- Confirm corpus metadata matches your needs

### 4. Test the Configuration

Start the application and verify the target loads correctly:

```bash
make b  # Start backend
# Check logs for configuration loading messages
```

## Memory and Performance Considerations

### Search-K (SEARCH_K) Impact

The `SEARCH_K` parameter directly affects memory usage and response quality:

- **k15**: ~15KB of context per query (memory efficient)
- **k20**: ~20KB of context per query (balanced)  
- **k30**: ~30KB of context per query (comprehensive but memory intensive)
- **k40+**: >40KB of context per query (high memory usage)

### Recommended Configurations

#### Development Environment
- **k15-k20**: Fast testing and development
- **Lower-tier models**: Cost-effective during development

#### Staging Environment  
- **k20-k30**: Representative of production load
- **Production models**: Accurate performance testing

#### Production Environment
- **k15-k25**: Optimized for concurrent users
- **Enterprise models**: Best quality and reliability

### Load Testing Optimization

For load testing, consider memory-optimized targets:
- **`k20_google_gemini_2.0`**: 33% memory reduction vs k30
- Lower `SEARCH_K` values reduce memory pressure
- Monitor semantic success rates to ensure quality

## Troubleshooting

### Configuration Not Loading
```
ERROR: No test target config file found for k15_claude37
```
**Solution**: Ensure `backend/targets/k15_claude37.txt` exists and is readable.

### Vector Store Mismatch
```
ERROR: Chroma collection 'blert_1000' not found
```
**Solution**: Verify `CHROMA_COLLECTION_NAME` matches an existing vector store directory.

### Embedding Model Mismatch
```
WARNING: Embedding model mismatch between config and vector store
```
**Solution**: Ensure `EMBEDDING_MODEL` in `.env` matches the model used to create the vector store.

### Memory Issues
```
ERROR: Worker process exceeded memory limit
```
**Solution**: Reduce `SEARCH_K` value or adjust worker memory limits in configuration.

## Best Practices

### Target Selection
1. **Match hardware capacity**: Use k15-k20 for 8vCPU/16GB, k30+ for larger systems
2. **Consider concurrent users**: Lower SEARCH_K for more concurrent capacity
3. **Balance quality vs performance**: Higher SEARCH_K improves results but uses more memory

### Configuration Management
1. **Use descriptive names**: Include key parameters in target names
2. **Version your targets**: Update TARGET_VERSION when making changes
3. **Document custom targets**: Add comments explaining configuration choices

### Testing and Validation
1. **Test new targets thoroughly**: Verify both functionality and performance
2. **Monitor memory usage**: Check system resources under load
3. **Compare semantic quality**: Evaluate answer quality across different configurations

---

Test targets provide the flexibility to optimize ATLAS for different use cases, from memory-constrained development environments to high-performance production systems. The integration with vector stores and retrievers creates a complete, configurable RAG pipeline.