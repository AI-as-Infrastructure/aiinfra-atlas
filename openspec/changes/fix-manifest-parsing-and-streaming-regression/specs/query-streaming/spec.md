# Query Streaming

## MODIFIED Requirements

### Requirement: User queries MUST complete without streaming errors

The `/api/ask/stream` endpoint MUST successfully stream LLM responses and return citations for wizard-built corpora. The streaming pipeline MUST NOT fail due to import changes, retriever misconfiguration, or unhandled exceptions in the citation formatting path.

#### Scenario: User submits a query against a wizard-built corpus

Given a corpus built via the corpus wizard with a valid ChromaDB collection and embedding model
When the user submits a question via the chat interface
Then the response streams successfully, citations are returned, and no streaming_error is sent to the frontend

#### Scenario: Citation formatting returns None for an invalid document

Given a document that causes format_document_for_citation() to return None
When the streaming pipeline processes references
Then the None result is skipped without raising a TypeError and remaining citations are still sent
