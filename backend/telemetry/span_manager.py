from contextlib import contextmanager
import time
from typing import Any, Dict, List, Optional

class BaseSpanManager:
    """Base class for managing telemetry spans with consistent attribute handling."""
    
    def __init__(self, tracer=None):
        """
        Initialize a span manager with a tracer.
        
        Args:
            tracer: OpenTelemetry tracer instance (if None, will use the default tracer)
        """
        self.tracer = tracer
        if not self.tracer:
            from opentelemetry import trace
            self.tracer = trace.get_tracer(__name__)
    
    @contextmanager
    def create_span(self, name: str, attributes: Optional[Dict[str, Any]] = None, 
                    info: Optional[Dict[str, Any]] = None, parent_span=None, 
                    session_id: str = None, qa_id: str = None):
        """
        Context manager for creating and managing spans with consistent attributes.
        
        Args:
            name: Name of the span
            attributes: Key-value pairs for span attributes
            info: Additional information to be logged separately from attributes
            parent_span: Optional parent span
            session_id: Optional session ID for linking
            qa_id: Optional question/answer ID for linking
        """
        # Initialize dictionaries if not provided
        attributes = attributes or {}
        info = info or {}
        
        # Add session and qa_id as standard attributes if provided
        if session_id:
            from .constants import SpanAttributes
            attributes[SpanAttributes.SESSION_ID] = session_id
        if qa_id:
            from .constants import SpanAttributes
            attributes[SpanAttributes.QA_ID] = qa_id
            
        # Start the span
        start_time = time.time()
        with self.tracer.start_as_current_span(name) as span:
            try:
                # Set all standard attributes directly on the span
                for key, value in attributes.items():
                    span.set_attribute(key, self._format_attribute_value(value))
                
                # Set info fields with consistent prefix to distinguish them
                for key, value in info.items():
                    info_key = f"info.{key}"
                    span.set_attribute(info_key, self._format_attribute_value(value))
                
                # Calculate and record duration both as start time and directly
                span.set_attribute("start_time", start_time)
                
                yield span
            except Exception as e:
                # Record error information
                span.set_attribute("error", True)
                span.set_attribute("error.message", str(e))
                span.set_attribute("error.type", e.__class__.__name__)
                span.record_exception(e)
                raise
            finally:
                # Record duration at the end
                duration = time.time() - start_time
                span.set_attribute("duration_ms", duration * 1000)
                
    def _format_attribute_value(self, value):
        """
        Format attribute values to ensure they're compatible with OpenTelemetry.
        Handles lists, dicts, and other common types.
        
        Args:
            value: The value to format
        
        Returns:
            Formatted value suitable for span attributes
        """
        import json
        
        # For None, return empty string
        if value is None:
            return ""
        
        # For basic types that OTel supports directly: str, bool, int, float
        if isinstance(value, (str, bool, int, float)):
            return value
            
        # For lists and dictionaries, stringify as JSON
        if isinstance(value, (list, dict)):
            try:
                return json.dumps(value)
            except:
                return str(value)
                
        # For all other types, convert to string
        return str(value)
        
    @staticmethod
    def set_standard_outputs(span, summary=None, details=None, error=None, span_kind=None):
        """
        Set standard output attributes for spans in a consistent way.
        
        Args:
            span: The span to update
            summary: A short summary of the operation result
            details: Detailed information about the operation
            error: Optional exception if an error occurred
            span_kind: The kind of span (retriever, LLM, etc.)
        """
        if summary:
            span.set_attribute("summary", summary)
            
        if details:
            # Format details as JSON for Phoenix UI
            import json
            try:
                span.set_attribute("details", json.dumps(details))
            except:
                span.set_attribute("details", str(details))
                
        if error:
            span.set_attribute("error", True)
            span.set_attribute("error.message", str(error))
            span.set_attribute("error.type", error.__class__.__name__)
            span.record_exception(error)
            
        if span_kind:
            span.set_attribute("openinference.span.kind", span_kind)
            
    @staticmethod
    def add_document_preview(span, documents, max_docs=3, max_length=200):
        """
        Add document preview information to a span.
        
        Args:
            span: The span to update
            documents: List of documents to preview
            max_docs: Maximum number of documents to preview
            max_length: Maximum length of each document preview
        """
        for i, doc in enumerate(documents[:max_docs]):
            if hasattr(doc, 'page_content'):
                content = doc.page_content[:max_length]
                if len(doc.page_content) > max_length:
                    content += "..."
                span.set_attribute(f"document.{i}.preview", content)
                
            # Add metadata
            if hasattr(doc, 'metadata'):
                for key, value in doc.metadata.items():
                    # Limit to important metadata fields
                    if key in ["date", "corpus", "title", "source"]:
                        span.set_attribute(f"document.{i}.{key}", str(value)) 
