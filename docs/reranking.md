# Document Reranking

## Overview

Document reranking is a crucial component in the ATLAS retrieval pipeline that improves search relevance by re-ordering retrieved documents. While vector similarity search provides a good initial set of relevant documents, the reranker applies additional relevance criteria to further refine these results based on query-specific analysis.

## How Reranking Works

The reranking module implements a multi-faceted scoring approach that considers:

1. **Exact Phrase Matches** - Documents containing the exact query phrase receive the highest priority
2. **Keyword Frequency** - Documents with more occurrences of query keywords are ranked higher
3. **Word Proximity** - Documents where query keywords appear close together are favored
4. **Metadata Matching** - Documents with query terms in metadata fields receive bonus points

This approach helps to surface truly relevant documents that might not have ranked highest in the initial vector similarity search.

## Configuration

The reranking algorithm provides several configuration parameters that can be adjusted to optimize its behavior for different document collections and query patterns. These parameters are defined at the top of the `document_reranking.py` module:

### Scoring Weights

| Parameter | Default | Description |
|-----------|---------|-------------|
| `WEIGHT_EXACT_MATCH` | 0.5 | Weight for exact phrase matches (0.0-1.0) |
| `WEIGHT_KEYWORD_FREQ` | 0.3 | Weight for keyword frequency (0.0-1.0) |
| `WEIGHT_PROXIMITY` | 0.2 | Weight for keyword proximity (0.0-1.0) |

*Note: Weights should sum to 1.0*

### Scoring Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `EXACT_MATCH_SCORE` | 10.0 | Base score for finding exact query match |
| `MAX_KEYWORD_SCORE` | 5.0 | Maximum score per keyword frequency |
| `PROXIMITY_WINDOW` | 50 | Character window for proximity detection |
| `METADATA_MATCH_BONUS` | 0.5 | Score bonus for each metadata match |
| `MAX_SCORE` | 10.0 | Maximum normalized score |

### Filter Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `MIN_TERM_LENGTH` | 3 | Minimum length for keywords to consider |
| `DEFAULT_MAX_DOCS` | 10 | Default number of documents to return |

## Dynamic Configuration

The reranker can be configured at runtime using the `configure_reranker()` function, which allows for dynamic adjustment of parameters without modifying code:

```python
from backend.modules.document_reranking import configure_reranker

# Adjust weights to emphasize keyword frequency over exact matches
new_config = configure_reranker({
    "weight_exact_match": 0.3,
    "weight_keyword_freq": 0.5,
    "weight_proximity": 0.2,
    "proximity_window": 100  # Widen proximity window
})
```

## Telemetry Integration

The reranking module includes built-in telemetry that tracks:

- Input/output document counts
- Processing time
- Score distribution (min, max, average)
- Per-document scores for top results

This data appears in Phoenix with the span type "RERANKER" and provides valuable insights for optimizing retrieval performance.

## Extensions

The modular design of the reranking system allows for implementing domain-specific scoring functions without modifying the core architecture. If your corpus has unique characteristics that could improve relevance, consider implementing a custom scoring function that builds upon the base `calculate_relevance_score()` function. 