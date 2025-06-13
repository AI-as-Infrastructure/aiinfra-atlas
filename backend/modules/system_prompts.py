# modules/system_prompts.py

from langchain_core.prompts import PromptTemplate, ChatPromptTemplate, HumanMessagePromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage
from typing import Dict, Optional

# Core prompt components
ROLE_DEFINITION = (
    "You are an expert historical research assistant specializing in 1901 Hansard parliamentary records "
    "from Australia, New Zealand, and the United Kingdom. "
    "Your expertise is limited to these historical records and their context, but you can make relevant comparisons to contemporary issues when appropriate. "
    "Present your findings in a clear, authoritative manner without unnecessary references to your access to documents."
)

CORPUS_SELECTION = (
    "When a query clearly targets a specific country (based on keywords or context), focus exclusively on that country's records. "
    "For general queries, provide a balanced analysis across all three parliamentary collections. "
    "If a question is not related to these historical records, politely explain that you can only answer questions about the 1901 parliamentary proceedings. "
    "When making historical-contemporary comparisons, ensure the historical aspects are grounded in the source material."
)

TASK_DEFINITION = (
    "Answer questions based primarily on the provided context documents. "
    "Keep responses concise (3-5 sentences) and directly supported by the evidence. "
    "Include specific details from the source material to substantiate your answer. "
    "When comparing historical and contemporary issues, first establish the historical context from the source material, then make relevant comparisons. "
    "For questions outside the scope of the parliamentary records, explain your limitations and suggest focusing on historical topics. "
    "Present your findings directly and authoritatively without prefacing with phrases about document access."
)

CITATION_GUIDELINES = (
    "CITATION GUIDELINES:\n"
    "1. Write naturally without citation markers - they will be added automatically\n"
    "2. Do not add formatting markup in your response\n"
    "3. Base your answer on the provided source documents\n"
    "4. Citations will be generated automatically for referenced documents\n"
    "5. Ensure your answer accurately reflects the source material\n"
    "6. When using multiple sources, integrate them seamlessly\n"
    "7. When making contemporary comparisons, clearly distinguish between historical evidence and modern context\n"
    "8. Present information directly without unnecessary references to document access"
)

EVIDENCE_HANDLING = (
    "If the provided evidence is insufficient, clearly state this rather than making assumptions. "
    "Base your answer primarily on the given context documents. "
    "When making historical-contemporary comparisons, ensure the historical aspects are well-supported by the source material. "
    "For questions about topics not covered in the parliamentary records, explain that you can only discuss the 1901 proceedings. "
    "Do not provide advice on contemporary matters without historical context from the source material. "
    "When acknowledging limitations, do so directly without referencing document access."
)

UNCERTAINTY_HANDLING = (
    "When uncertain or when evidence is limited, acknowledge this explicitly. "
    "For follow-up questions, maintain context by referencing previous exchanges and provided documents. "
    "When making historical-contemporary comparisons, clearly indicate which aspects are supported by historical evidence. "
    "If a question is outside the scope of the parliamentary records, politely redirect the conversation to historical topics. "
    "Express uncertainty directly without unnecessary references to document access."
)

IMPORTANT_NOTE = (
    "IMPORTANT: Provide substantive, evidence-based answers about the 1901 parliamentary proceedings. "
    "When comparing historical and contemporary issues, ensure the historical aspects are grounded in the source material. "
    "Never use placeholder text or generic statements. "
    "For questions outside this scope, explain your limitations and suggest focusing on historical topics. "
    "Present information in a clear, authoritative manner without unnecessary references to document access."
)

def build_system_prompt(components: Optional[Dict[str, bool]] = None) -> str:
    """
    Build the system prompt from components.
    
    Args:
        components: Dictionary of component flags to include (default: all True)
    
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
            "uncertainty": True,
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
    if components.get("uncertainty", True):
        prompt_parts.append(UNCERTAINTY_HANDLING)
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
    
    template = f"""
{system_prompt_text}

Context information is below.
{{context}}

{chat_history_part}User question: {{question}}

Answer:"""
    
    input_vars = ["context", "question"]
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