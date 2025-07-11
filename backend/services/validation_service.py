#!/usr/bin/env python3
"""
Session Validation Service for ATLAS

Provides validation of RAG sessions using alternate LLMs to provide
structured feedback and quality assessment.
"""

import os
import logging
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from backend.modules.llm import create_llm
from backend.modules.config import get_llm_config
from backend.telemetry import create_span, SpanAttributes, SpanNames, OpenInferenceSpanKind

logger = logging.getLogger(__name__)

@dataclass
class ValidationConfig:
    """Configuration for session validation"""
    mode: str  # "default" or "alternate"
    default_model: str
    alternate_model: str
    default_provider: str
    alternate_provider: str
    enabled: bool

@dataclass
class SessionData:
    """Structure for session data to be validated"""
    session_id: str
    qa_id: str
    question: str
    answer: str
    citations: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    timestamp: Optional[str] = None

@dataclass
class ValidationResult:
    """Result of session validation"""
    session_id: str
    qa_id: str
    validation_model: str
    validation_provider: str
    validation_mode: str
    feedback: str
    structured_feedback: Dict[str, Any]
    validation_timestamp: str
    processing_time: float

class ValidationService:
    """Service for validating RAG sessions using LLMs"""
    
    def __init__(self):
        self.config = self._load_config()
        self.validation_prompts = self._load_validation_prompts()
        
    def _load_config(self) -> ValidationConfig:
        """Load validation configuration from environment"""
        return ValidationConfig(
            mode=os.getenv("VALIDATION_LLM_MODE", "alternate"),
            default_model=os.getenv("VALIDATION_LLM_DEFAULT", "gpt-4o"),
            alternate_model=os.getenv("VALIDATION_LLM_ALTERNATE", "claude-3-5-sonnet-20241022"),
            default_provider=os.getenv("VALIDATION_PROVIDER_DEFAULT", "OPENAI"),
            alternate_provider=os.getenv("VALIDATION_PROVIDER_ALTERNATE", "ANTHROPIC"),
            enabled=os.getenv("VALIDATION_ENABLED", "true").lower() == "true"
        )
    
    def _load_validation_prompts(self) -> Dict[str, str]:
        """Load validation prompt templates"""
        return {
            "system_prompt": """You are an expert evaluator of RAG (Retrieval-Augmented Generation) systems for historical parliamentary documents. Your task is to provide structured feedback on the quality and accuracy of generated responses.

Evaluate the following aspects:
1. **Factual Accuracy**: Are the facts presented correct and verifiable from the source documents?
2. **Completeness**: Does the answer address all aspects of the question?
3. **Relevance**: Is the information relevant to the user's query?
4. **Citation Quality**: Are the sources appropriate and properly referenced?
5. **Clarity**: Is the response clear and well-structured?
6. **Historical Context**: Is the historical context accurate and appropriate?

Provide your feedback in the following JSON structure:
{
  "overall_quality": "excellent|good|fair|poor",
  "factual_accuracy": {
    "score": 1-5,
    "issues": ["list of specific factual issues"],
    "verification_notes": "notes about fact-checking"
  },
  "completeness": {
    "score": 1-5,
    "missing_aspects": ["aspects not addressed"],
    "coverage_notes": "notes about question coverage"
  },
  "relevance": {
    "score": 1-5,
    "relevance_issues": ["off-topic or irrelevant content"],
    "relevance_notes": "notes about relevance"
  },
  "citation_quality": {
    "score": 1-5,
    "citation_issues": ["problems with sources"],
    "source_notes": "notes about source quality"
  },
  "clarity": {
    "score": 1-5,
    "clarity_issues": ["unclear or confusing parts"],
    "clarity_notes": "notes about presentation"
  },
  "historical_context": {
    "score": 1-5,
    "context_issues": ["historical inaccuracies"],
    "context_notes": "notes about historical accuracy"
  },
  "recommendations": ["specific suggestions for improvement"],
  "strengths": ["what the response does well"],
  "overall_notes": "summary assessment"
}""",
            
            "user_prompt_template": """Please evaluate this RAG system response:

## Original Question
{question}

## Generated Answer
{answer}

## Source Documents Used
{citations}

## System Metadata
- Model: {model}
- Retriever: {retriever}
- Target Configuration: {target_config}
- Processing Time: {processing_time}
- Timestamp: {timestamp}

## Validation Request
Please provide structured feedback on this response according to the evaluation criteria outlined in the system prompt. Focus on accuracy, completeness, and the quality of the historical information provided."""
        }
    
    def is_enabled(self) -> bool:
        """Check if validation is enabled"""
        return self.config.enabled
    
    def get_validation_model_info(self) -> Dict[str, str]:
        """Get information about the current validation model configuration"""
        if self.config.mode == "default":
            return {
                "model": self.config.default_model,
                "provider": self.config.default_provider,
                "mode": "default"
            }
        else:
            return {
                "model": self.config.alternate_model,
                "provider": self.config.alternate_provider,
                "mode": "alternate"
            }
    
    def export_session_to_markdown(self, session_data: SessionData) -> str:
        """Export session data to structured Markdown format"""
        # Format citations
        citations_md = ""
        if session_data.citations:
            citations_md = "\n".join([
                f"- **{citation.get('title', 'Unknown Title')}**"
                f"\n  - Date: {citation.get('date', 'Unknown')}"
                f"\n  - Source: {citation.get('corpus', 'Unknown')}"
                f"\n  - Content: {citation.get('content', '')[:200]}..."
                f"\n  - URL: {citation.get('url', 'N/A')}"
                for citation in session_data.citations[:5]  # Limit to first 5
            ])
        else:
            citations_md = "No citations available"
        
        # Format metadata
        metadata_md = ""
        if session_data.metadata:
            metadata_md = "\n".join([
                f"- **{key}**: {value}" 
                for key, value in session_data.metadata.items()
            ])
        
        # Create structured Markdown
        markdown = f"""# RAG Session Validation Report

## Session Information
- **Session ID**: {session_data.session_id}
- **QA ID**: {session_data.qa_id}
- **Timestamp**: {session_data.timestamp or datetime.now().isoformat()}

## User Question
{session_data.question}

## Generated Answer
{session_data.answer}

## Source Documents
{citations_md}

## System Metadata
{metadata_md}

## Validation Instructions
Please evaluate this RAG response for:
1. Factual accuracy against the source documents
2. Completeness in addressing the user's question
3. Relevance of the information provided
4. Quality and appropriateness of citations
5. Clarity and structure of the response
6. Historical context accuracy

Provide specific feedback on strengths, weaknesses, and recommendations for improvement.
"""
        return markdown
    
    def validate_session(self, session_data: SessionData, 
                        validation_mode: Optional[str] = None) -> ValidationResult:
        """Validate a RAG session using the configured LLM"""
        
        if not self.is_enabled():
            raise ValueError("Session validation is disabled")
        
        # Use provided mode or fall back to configured mode
        mode = validation_mode or self.config.mode
        
        # Get validation model configuration
        if mode == "default":
            model = self.config.default_model
            provider = self.config.default_provider
        else:
            model = self.config.alternate_model
            provider = self.config.alternate_provider
        
        start_time = datetime.now()
        
        # Run validation without creating a separate span - results will be attached as annotations
        try:
            # Create LLM instance for validation
            validation_llm = create_llm(
                model_name=model,
                provider=provider,
                temperature=0.1,  # Low temperature for consistent evaluation
                streaming=False
            )
            
            # Format citations for the prompt
            citations_text = self._format_citations_for_prompt(session_data.citations)
            
            # Prepare validation prompt
            user_prompt = self.validation_prompts["user_prompt_template"].format(
                question=session_data.question,
                answer=session_data.answer,
                citations=citations_text,
                model=session_data.metadata.get("model", "Unknown"),
                retriever=session_data.metadata.get("retriever", "Unknown"),
                target_config=session_data.metadata.get("target_config", "Unknown"),
                processing_time=session_data.metadata.get("processing_time", "Unknown"),
                timestamp=session_data.timestamp or datetime.now().isoformat()
            )
            
            # Create messages for the validation LLM
            messages = [
                {"role": "system", "content": self.validation_prompts["system_prompt"]},
                {"role": "user", "content": user_prompt}
            ]
            
            # Generate validation response
            validation_response = validation_llm.invoke(messages)
            
            if hasattr(validation_response, 'content'):
                feedback_text = validation_response.content
            else:
                feedback_text = str(validation_response)
            
            # Try to parse structured feedback
            structured_feedback = self._parse_structured_feedback(feedback_text)
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Create validation result
            result = ValidationResult(
                session_id=session_data.session_id,
                qa_id=session_data.qa_id,
                validation_model=model,
                validation_provider=provider,
                validation_mode=mode,
                feedback=feedback_text,
                structured_feedback=structured_feedback,
                validation_timestamp=datetime.now().isoformat(),
                processing_time=processing_time
            )
            
            logger.info(f"Session validation completed for {session_data.session_id} using {provider}/{model}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error during session validation: {e}")
            raise
    
    def _format_citations_for_prompt(self, citations: List[Dict[str, Any]]) -> str:
        """Format citations for inclusion in validation prompt"""
        if not citations:
            return "No citations provided"
        
        formatted_citations = []
        for i, citation in enumerate(citations[:5], 1):  # Limit to first 5
            formatted_citations.append(f"""
{i}. **{citation.get('title', 'Unknown Title')}**
   - Date: {citation.get('date', 'Unknown')}
   - Source: {citation.get('corpus', 'Unknown')}
   - Content Preview: {citation.get('content', '')[:300]}...
   - URL: {citation.get('url', 'N/A')}
""")
        
        return "\n".join(formatted_citations)
    
    def _parse_structured_feedback(self, feedback_text: str) -> Dict[str, Any]:
        """Parse structured feedback from LLM response"""
        try:
            # Try to find JSON in the response - look for multiple possible JSON blocks
            import re
            
            # First try to find the main JSON block starting with {
            json_match = re.search(r'\{.*\}', feedback_text, re.DOTALL)
            if json_match:
                json_text = json_match.group(0)
                try:
                    parsed = json.loads(json_text)
                    logger.info(f"Successfully parsed structured feedback: {json.dumps(parsed, indent=2)}")
                    return parsed
                except json.JSONDecodeError:
                    pass
            
            # If that fails, try to find JSON between ```json blocks
            json_block_match = re.search(r'```json\s*(.*?)\s*```', feedback_text, re.DOTALL)
            if json_block_match:
                json_text = json_block_match.group(1)
                try:
                    parsed = json.loads(json_text)
                    logger.info(f"Successfully parsed structured feedback from code block: {json.dumps(parsed, indent=2)}")
                    return parsed
                except json.JSONDecodeError:
                    pass
            
            # If JSON parsing fails, try to extract basic information with regex
            logger.warning("JSON parsing failed, attempting to extract basic info from text")
            
            # Extract overall quality
            overall_quality = "unknown"
            quality_match = re.search(r'"overall_quality":\s*"([^"]+)"', feedback_text)
            if quality_match:
                overall_quality = quality_match.group(1)
            else:
                # Try alternative patterns
                if re.search(r'\bexcellent\b', feedback_text, re.IGNORECASE):
                    overall_quality = "excellent"
                elif re.search(r'\bgood\b', feedback_text, re.IGNORECASE):
                    overall_quality = "good"
                elif re.search(r'\bfair\b', feedback_text, re.IGNORECASE):
                    overall_quality = "fair"
                elif re.search(r'\bpoor\b', feedback_text, re.IGNORECASE):
                    overall_quality = "poor"
            
            # Extract numeric scores if possible
            scores = {}
            for category in ['factual_accuracy', 'completeness', 'relevance', 'citation_quality', 'clarity', 'historical_context']:
                score_match = re.search(rf'"{category}":\s*\{{\s*"score":\s*(\d+)', feedback_text)
                if score_match:
                    scores[category] = {"score": int(score_match.group(1))}
            
            result = {
                "overall_quality": overall_quality,
                "raw_feedback": feedback_text,
                "parse_error": "Could not parse full JSON structure",
                **scores
            }
            
            logger.info(f"Extracted basic feedback info: {json.dumps(result, indent=2)}")
            return result
            
        except Exception as e:
            logger.error(f"Error parsing structured feedback: {e}")
            return {
                "overall_quality": "unknown",
                "raw_feedback": feedback_text,
                "parse_error": f"Parsing error: {str(e)}"
            }
    
    def get_validation_config_info(self) -> Dict[str, Any]:
        """Get current validation configuration information"""
        return {
            "enabled": self.config.enabled,
            "mode": self.config.mode,
            "current_model": self.get_validation_model_info(),
            "available_modes": ["default", "alternate"],
            "default_model": f"{self.config.default_provider}/{self.config.default_model}",
            "alternate_model": f"{self.config.alternate_provider}/{self.config.alternate_model}"
        }

# Global instance
validation_service = ValidationService()