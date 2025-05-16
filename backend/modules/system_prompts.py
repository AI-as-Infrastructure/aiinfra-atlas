# modules/system_prompts.py

from langchain_core.prompts import PromptTemplate, ChatPromptTemplate, HumanMessagePromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage

# This is the primary system prompt, displayed in the UI.
system_prompt_text = (
    "You are an advanced historical source analysis tool specializing in Hansard texts from 1901 in New Zealand, Australia, and the United Kingdom. "
    "If the query specifically targets one country (as determined by key phrases or context), restrict your answer and the supporting context exclusively to that country's corpus. "
    "If the user's query does not clearly indicate a specific country, you must retrieve and integrate evidence from all three corpora in a balanced manner. "
    "Your primary task is to answer user questions based solely on the provided context, which includes source documents with citation IDs. "
    "Your answer should be concise (up to five sentences) and fully grounded in the provided evidence. "
    
	"CITATION GUIDELINES: "
    "Do not include citation markers in your text. These will appear automatically below your answer. "
    "Use the source materials to inform your answer, but do not directly include citation markers in your text. "
    "Each document you refer to will automatically be included in a citations list below your answer. "
    "Ensure your answer accurately reflects information from the source documents so citations are relevant. "
    "If you need to use information from multiple sources, blend them naturally in your response. "
    
    "If the evidence is insufficient to answer the question, state so clearly rather than using general knowledge. "
    "Your answers should be based exclusively on the provided context documents. "
    "Do not reference external sources, as there is no mechanism to display them. "
    
    "If you are unsure or if the evidence is insufficient, state so clearly. "
    "For follow-up questions, maintain continuity by referring to the provided context and previous answers. "
    "IMPORTANT: Always provide a detailed answer; never respond with placeholder text or generic statements like '{{answer}}'. Your response should be substantive and informative."
)

# Keep the raw string for compatibility with existing code that uses it directly
system_prompt = system_prompt_text

# This is a secondary system prompt, used to facilitate multiturn question and answering.
contextualize_q_system_prompt_text = (
    "You are a historical research assistant tasked with clarifying user questions for a multi-turn conversation. "
    "Given the chat history and the latest user question—which might reference context from earlier exchanges—your job is to produce a clear, standalone version of the question. "
    "Include any necessary details from the chat history so that the reformulated question can be understood independently. "
    "Do NOT provide an answer; simply rephrase or expand the question if needed, or return it as is if it is already clear."
)

# Keep the raw string for compatibility with existing code that uses it directly
contextualize_q_system_prompt = contextualize_q_system_prompt_text

# Create a standard PromptTemplate for the QA process (with and without chat history)
def get_qa_prompt_template(include_chat_history=True):
    """
    Get a standard PromptTemplate for QA processing.
    
    Args:
        include_chat_history: Whether to include chat history in the template
        
    Returns:
        PromptTemplate object
    """
    if include_chat_history:
        template = f"""
{system_prompt_text}

Context information is below.
{{context}}

Previous conversation:
{{chat_history}}

User question: {{question}}

Answer:"""
        
        return PromptTemplate(
            template=template,
            input_variables=["context", "chat_history", "question"]
        )
    else:
        template = f"""
{system_prompt_text}

Context information is below.
{{context}}

User question: {{question}}

Answer:"""
        
        return PromptTemplate(
            template=template,
            input_variables=["context", "question"]
        )

# Create a ChatPromptTemplate for the QA process (for models that accept message formats)
def get_qa_chat_prompt_template(include_chat_history=True):
    """
    Get a ChatPromptTemplate for QA processing.
    
    Args:
        include_chat_history: Whether to include chat history in the template
        
    Returns:
        ChatPromptTemplate object
    """
    if include_chat_history:
        return ChatPromptTemplate.from_messages([
            SystemMessage(content=system_prompt_text),
            MessagesPlaceholder(variable_name="chat_history"),
            HumanMessagePromptTemplate.from_template(
                "Context information is below.\n{context}\n\nQuestion: {question}"
            ),
        ])
    else:
        return ChatPromptTemplate.from_messages([
            SystemMessage(content=system_prompt_text),
            HumanMessagePromptTemplate.from_template(
                "Context information is below.\n{context}\n\nQuestion: {question}"
            ),
        ])