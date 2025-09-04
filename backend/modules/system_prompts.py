# modules/system_prompts.py

from langchain_core.prompts import PromptTemplate, ChatPromptTemplate, HumanMessagePromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage
from typing import Dict, Optional

# Core prompt components
ROLE_DEFINITION = (
    "You are a 1901 Hansard parliamentary records expert (Australia, New Zealand, United Kingdom). "
    "Provide well-structured responses of 200-300 words using only the provided context. "
    "Write in clear, academic prose with proper paragraph structure. "
    "Include key details, quotes, and evidence to address parliamentary questions effectively."
)

CORPUS_SELECTION = (
    "FILTERED queries (single country selected): Focus exclusively on that country's records. "
    "UNFILTERED queries (all countries): Compare and contrast across UK, Australia, and New Zealand. Highlight similarities, differences, and interactions between parliamentary approaches. "
    "Off-topic questions: redirect to 1901 parliamentary topics."
)

TASK_DEFINITION = (
    "Use ONLY the provided context documents. Provide thorough, evidence-based responses. "
    "Start with a direct answer, then elaborate with relevant evidence and examples. "
    "Include specific details, member names, dates, and parliamentary procedures when available. "
    "If context is insufficient: ask for question refinement. Off-topic: redirect briefly to 1901 parliamentary topics."
)

CITATION_GUIDELINES = (
    "Write naturally - citations auto-generated. Integrate multiple sources seamlessly."
)

EVIDENCE_HANDLING = (
    "Context-only responses. No external knowledge. No unsupported claims."
)

MANIFEST_USAGE = (
    "Repository stats: use only manifest.json data. Content questions: use context documents only."
)

UNCERTAINTY_HANDLING = (
    "Acknowledge uncertainty explicitly. Maintain context in follow-ups."
)

SEARCH_GUIDANCE = (
    "Insufficient context: suggest more specific questions. Guide better formulation, not technical limitations."
)

IMPORTANT_NOTE = (
    "Provide comprehensive, well-researched answers using the provided parliamentary documents. "
    "Structure responses clearly and include sufficient detail to fully address the research question."
)

def build_system_prompt(components: Optional[Dict[str, bool]] = None) -> str:
    """
    Build the system prompt from components.
    
    Args:
        components: Dictionary of component flags to include (default: essential only)
    
    Returns:
        str: Complete system prompt
    """
    if components is None:
        components = {
            "role": True,
            "corpus": True,
            "task": True,
            "citations": True,
            "evidence": True,
            "manifest": True,
            "uncertainty": True,
            "search_guidance": True,
            "important": True
        }
    
    prompt_parts = []
    
    if components.get("role", True):
        prompt_parts.append(ROLE_DEFINITION)
    if components.get("corpus", True):
        prompt_parts.append(CORPUS_SELECTION)
    if components.get("task", True):
        prompt_parts.append(TASK_DEFINITION)
    if components.get("citations", True):
        prompt_parts.append(CITATION_GUIDELINES)
    if components.get("evidence", True):
        prompt_parts.append(EVIDENCE_HANDLING)
    if components.get("manifest", True):
        prompt_parts.append(MANIFEST_USAGE)
    if components.get("uncertainty", True):
        prompt_parts.append(UNCERTAINTY_HANDLING)
    if components.get("search_guidance", True):
        prompt_parts.append(SEARCH_GUIDANCE)
    if components.get("important", True):
        prompt_parts.append(IMPORTANT_NOTE)
    
    return " ".join(prompt_parts)

# Primary system prompt - maintain these variables for UI compatibility
system_prompt_text = build_system_prompt()
system_prompt = system_prompt_text

# Contextualization prompt for multi-turn conversations
contextualize_q_system_prompt_text = (
    "You are a historical research assistant clarifying questions for a multi-turn conversation.\n"
    "Given the chat history and current question, produce a clear, standalone version that captures all relevant context.\n"
    "Include necessary details from previous exchanges to ensure the question is self-contained.\n"
    "If the question involves historical-contemporary comparisons, ensure the historical aspects are clearly identified.\n"
    "If the question is not about the 1901 parliamentary records, note this in your reformulation.\n"
    "Do not provide an answer - only rephrase or expand the question if needed."
)
contextualize_q_system_prompt = contextualize_q_system_prompt_text

def get_qa_prompt_template(include_chat_history: bool = True) -> PromptTemplate:
    """
    Get a standard PromptTemplate for QA processing.
    
    Args:
        include_chat_history: Whether to include chat history in the template
        
    Returns:
        PromptTemplate object
    """
    # Build the template parts separately
    chat_history_part = "Previous conversation:\n{chat_history}\n\n" if include_chat_history else ""
    
    # Dynamic corpus instruction based on filter
    corpus_instruction = """
Query scope: {corpus_scope}

"""
    
    template = f"""
{system_prompt_text}

{corpus_instruction}Context information is below.
{{context}}

{chat_history_part}User question: {{question}}

Answer:"""
    
    input_vars = ["context", "question", "corpus_scope"]
    if include_chat_history:
        input_vars.append("chat_history")
    
    return PromptTemplate(
        template=template,
        input_variables=input_vars
    )

def get_qa_chat_prompt_template(include_chat_history: bool = True) -> ChatPromptTemplate:
    """
    Get a ChatPromptTemplate for QA processing.
    
    Args:
        include_chat_history: Whether to include chat history in the template
        
    Returns:
        ChatPromptTemplate object
    """
    messages = [
        SystemMessage(content=system_prompt_text),
        HumanMessagePromptTemplate.from_template(
            "Context information is below.\n{context}\n\nQuestion: {question}"
        )
    ]
    
    if include_chat_history:
        messages.insert(1, MessagesPlaceholder(variable_name="chat_history"))
    
    return ChatPromptTemplate.from_messages(messages)