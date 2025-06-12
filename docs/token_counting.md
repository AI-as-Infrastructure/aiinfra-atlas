# Provider-Agnostic Token Counting for Phoenix Telemetry

This module provides token counting functionality that works across different LLM providers (OpenAI, Anthropic, Ollama, Bedrock, etc.) with appropriate fallbacks for Phoenix observability.

## How It Works

### Provider-Specific Token Extraction

The system attempts to extract actual token counts from LLM responses based on the provider:

1. **OpenAI**: Extracts from `response.usage.prompt_tokens`, `completion_tokens`, `total_tokens`
2. **Anthropic**: Extracts from `response.usage.input_tokens`, `output_tokens` 
3. **Ollama**: Extracts from `response.prompt_eval_count`, `eval_count`
4. **Generic**: Tries common field names for unknown providers

### Fallback Estimation Methods

When exact token counts aren't available, the system provides multiple estimation methods:

1. **tiktoken (preferred)**: Uses OpenAI's tiktoken library for accurate token estimation
2. **Character-based**: Estimates tokens using average 4 characters per token
3. **Word-based**: Estimates using average 1.3 tokens per word

## Phoenix Integration

The token counts are automatically added to LLM spans using OpenInference standard attributes:

- `llm.token_count.prompt` - Input tokens
- `llm.token_count.completion` - Output tokens  
- `llm.token_count.total` - Total tokens

Phoenix automatically aggregates these across all LLM spans in a trace for the cumulative token display.

## Usage

### Automatic Integration

Token counting is automatically integrated into the LLM generation telemetry:

```python
# Token counts are automatically added to LLM spans
response_gen, qa_id = generate_response_with_telemetry(
    question="What is the capital of France?",
    documents=retrieved_docs,
    session_id=session_id,
    provider="openai"  # or "anthropic", "ollama", etc.
)
```

### Manual Usage

You can also add token counts to custom spans:

```python
from backend.telemetry.token_counting import add_token_counts_to_span

# Add token counts to any span
add_token_counts_to_span(
    span=your_span,
    prompt_text="Your prompt text here",
    completion_text="Generated response text",
    response_obj=llm_response,  # Optional: actual LLM response object
    provider="openai"
)
```

### Direct Token Counter Usage

For advanced use cases, you can use the TokenCounter directly:

```python
from backend.telemetry.token_counting import get_token_counter

counter = get_token_counter("openai")

# Extract from response object
tokens = counter.extract_tokens_from_response(llm_response)

# Estimate from text
prompt_tokens = counter.estimate_tokens("Your prompt text", method="tiktoken")

# Calculate comprehensive token counts
tokens = counter.calculate_token_counts(
    prompt_text="Your prompt",
    completion_text="Generated response",
    response_obj=llm_response
)
```

## Provider Support

### Fully Supported
- **OpenAI**: Extracts exact token counts from API responses
- **Anthropic**: Extracts exact token counts using Claude's response format

### Partially Supported  
- **Ollama**: May provide token counts depending on model
- **Bedrock**: Generic extraction attempted

### Fallback Support
- **Any Provider**: Uses tiktoken or character/word estimation when exact counts unavailable

## Configuration

The system automatically detects the provider from your LLM configuration. No additional setup is required.

### Optional tiktoken Installation

For the most accurate token estimation, ensure tiktoken is installed:

```bash
pip install tiktoken==0.9.0  # Already in requirements.txt
```

## Phoenix UI Display

Once implemented, you'll see:

1. **Individual span token counts** in the span attributes
2. **Cumulative token counts** at the trace level
3. **Token cost calculations** (if Phoenix is configured with pricing)

## Troubleshooting

### Token Counts Show as Zero

1. Check if your LLM provider returns usage information
2. Verify tiktoken is installed for estimation fallback
3. Enable debug logging to see token counting attempts

### Inaccurate Estimates

1. For OpenAI models, tiktoken provides accurate estimates
2. For other providers, estimates are approximations
3. Consider implementing provider-specific token counting

### Performance Considerations

1. Token counting adds minimal overhead (~1-2ms)
2. tiktoken encoding is cached for efficiency
3. Estimation fallbacks are very fast

## Examples

### OpenAI with Exact Counts
```python
# OpenAI returns exact token usage
tokens = {
    "prompt_tokens": 150,
    "completion_tokens": 85, 
    "total_tokens": 235
}
```

### Ollama with Estimation
```python
# Ollama may not provide counts, uses tiktoken estimation
tokens = {
    "prompt_tokens": 142,  # Estimated via tiktoken
    "completion_tokens": 78,   # Estimated via tiktoken
    "total_tokens": 220
}
```

This system ensures comprehensive token tracking across all providers while maintaining Phoenix observability standards. 