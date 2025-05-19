from contextlib import contextmanager
from .span_manager import BaseSpanManager
from .constants import SpanNames, SpanAttributes, OpenInferenceSpanKind

class RAGSpanManager(BaseSpanManager):
    """Specialized span manager for RAG operations."""
    
    @contextmanager
    def retrieval_span(self, query, corpus_filter=None, session_id=None, qa_id=None, **extra_info):
        """
        Context manager for document retrieval spans.
        
        Args:
            query: The search query
            corpus_filter: Optional corpus filter
            session_id: Session ID
            qa_id: Question/answer ID
            extra_info: Any additional info fields
        """
        # Define standard attributes for retrieval spans
        attributes = {
            SpanAttributes.INPUT_VALUE: query,
            "openinference.span.kind": OpenInferenceSpanKind.RETRIEVER,
        }
        
        # Add corpus filter if provided
        if corpus_filter:
            attributes["corpus_filter"] = corpus_filter
        
        # Everything else goes into info
        with self.create_span(
            SpanNames.CONTEXT_RETRIEVAL,
            attributes=attributes,
            info=extra_info,
            session_id=session_id,
            qa_id=qa_id
        ) as span:
            yield span
            
    @contextmanager
    def ranking_span(self, document_count, session_id=None, qa_id=None, **extra_info):
        """Context manager for document ranking spans."""
        attributes = {
            SpanAttributes.DOCUMENT_COUNT: document_count,
            "openinference.span.kind": OpenInferenceSpanKind.RERANKER,
        }
        
        with self.create_span(
            SpanNames.DOCUMENT_RANKING,
            attributes=attributes,
            info=extra_info,
            session_id=session_id,
            qa_id=qa_id
        ) as span:
            yield span
    
    @contextmanager
    def llm_generation_span(self, model_name, prompt, context_document_count, 
                           session_id=None, qa_id=None, **extra_info):
        """Context manager for LLM generation spans."""
        attributes = {
            "openinference.llm.model_name": model_name,
            "openinference.span.kind": OpenInferenceSpanKind.LLM,
            "context_document_count": context_document_count,
        }
        
        # Add prompt and other sensitive data to info, not attributes
        info = extra_info.copy()
        info["prompt"] = prompt
        
        with self.create_span(
            SpanNames.LLM_GENERATION,
            attributes=attributes,
            info=info,
            session_id=session_id,
            qa_id=qa_id
        ) as span:
            yield span
            
    @contextmanager
    def citation_formatting_span(self, document_count, session_id=None, qa_id=None, **extra_info):
        """Context manager for citation formatting spans."""
        attributes = {
            SpanAttributes.DOCUMENT_COUNT: document_count,
            "openinference.span.kind": OpenInferenceSpanKind.REFERENCES,
        }
        
        with self.create_span(
            SpanNames.DOCUMENT_REFERENCES,
            attributes=attributes,
            info=extra_info,
            session_id=session_id,
            qa_id=qa_id
        ) as span:
            yield span 