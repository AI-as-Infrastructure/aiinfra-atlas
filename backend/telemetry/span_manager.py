from contextlib import contextmanager
import time
from typing import Any, Dict, List, Optional
import json

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
            info: Additional information to be added as regular attributes
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
            
        # Add info fields as regular attributes (without info. prefix)
        if info:
            for key, value in info.items():
                # Add directly to attributes with a flat name (no info. prefix)
                attributes[key] = self._format_attribute_value(value)
            
        # Start the span
        start_time = time.time()
        with self.tracer.start_as_current_span(name) as span:
            try:
                # Set all standard attributes directly on the span
                for key, value in attributes.items():
                    span.set_attribute(key, self._format_attribute_value(value))
                
                # Calculate and record duration both as start time and directly
                span.set_attribute("start_time", start_time)
                
                # Add the standard set_output method if not present
                if not hasattr(span, "set_output"):
                    def set_output(output):
                        if output:
                            # Set standard output fields for Phoenix
                            span.set_attribute("output.value", self._format_attribute_value(output))
                            span.set_attribute("content", self._format_attribute_value(output))
                            
                            # You can add more fields as needed for compatibility
                            if "LLM" in name or "llm" in name:
                                span.set_attribute("openinference.llm.output", self._format_attribute_value(output))
                            
                    span.set_output = set_output
                
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
    def set_standard_outputs(span, summary=None, details=None, error=None, span_kind=None, output=None):
        """
        Set standard output attributes for spans in a consistent way,
        optimized for Phoenix display using flat attribute names.
        
        Args:
            span: The span to update
            summary: A short summary of the operation result
            details: Detailed information about the operation
            error: Optional exception if an error occurred
            span_kind: The kind of span (retriever, LLM, etc.)
            output: Optional output content to set
        """
        # Set the summary as a flat attribute
        if summary:
            span.set_attribute("summary", summary)
            
        # Format details with proper structure for Phoenix
        if details:
            # Format details as JSON for Phoenix UI
            import json
            try:
                # Store the full details as a JSON string
                span.set_attribute("details", json.dumps(details))
                
                # Add a few key details as direct attributes for filtering/querying
                if isinstance(details, dict):
                    for key in ["document_count", "citation_count", "generation_time_seconds", "error"]:
                        if key in details:
                            span.set_attribute(key, details[key])
            except:
                span.set_attribute("details", str(details))
        
        # Set the output using appropriate methods
        if output:
            # Use set_output method if available
            if hasattr(span, "set_output"):
                span.set_output(output)
            else:
                # Fall back to direct attribute setting
                span.set_attribute("output.value", str(output))
                # Set content directly for all spans - this is what Phoenix UI displays
                span.set_attribute("content", str(output))
                
        # Error information is set directly as attributes for better visibility
        if error:
            span.set_attribute("error", True)
            span.set_attribute("error.message", str(error))
            span.set_attribute("error.type", error.__class__.__name__)
            span.record_exception(error)
            
        # Set the span kind attribute if provided - ensure it's in the attributes
        if span_kind:
            span.set_attribute("openinference.span.kind", span_kind)
            span.set_attribute("span.kind", span_kind)
            
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
        # Add a count to attributes for easy filtering
        span.set_attribute("document_preview_count", min(len(documents), max_docs))
        
        # Create a consolidated preview string for better display in Phoenix
        preview_texts = []
        
        # Process each document
        for i, doc in enumerate(documents[:max_docs]):
            if hasattr(doc, 'page_content'):
                # Get content preview with truncation
                content = doc.page_content[:max_length]
                if len(doc.page_content) > max_length:
                    content += "..."
                
                # Build metadata string for display
                meta = []
                if hasattr(doc, 'metadata'):
                    for key in ["date", "corpus", "title", "source"]:
                        if key in doc.metadata:
                            meta.append(f"{key}: {doc.metadata[key]}")
                
                # Create formatted document preview
                preview = f"Document {i+1} [{', '.join(meta)}]\n{content}"
                preview_texts.append(preview)
                
                # Set individual document attributes with flat names
                span.set_attribute(f"doc_{i}_content", content)
                
                # Add metadata with flat attribute names
                if hasattr(doc, 'metadata'):
                    for key in ["date", "corpus", "title", "source"]:
                        if key in doc.metadata:
                            span.set_attribute(f"doc_{i}_{key}", str(doc.metadata[key]))
        
        # Set consolidated preview for better display in Phoenix UI
        if preview_texts:
            span.set_attribute("document_previews", "\n\n".join(preview_texts)) 
