# chat.py
"""
GROQ LLM integration for RAG responses.
Provides structured prompting and error handling for production use.
"""
import functools
from typing import List, Dict, Any, Optional
from groq import Groq
from langchain_core.prompts import PromptTemplate
from app.core.config import settings
from app.core.logging import logger

# System prompt for RAG responses
_SYSTEM_PROMPT = """You are a helpful AI assistant that answers questions using the provided context and conversation history.

Guidelines:
- Use information from the provided context to answer questions
- Pay attention to the conversation history to understand context and references (like "it", "that", "this", etc.)
- If the current question refers to something mentioned in previous conversation turns, use that context to provide a better answer
- If the answer is not contained in the context or conversation history, say "I don't have enough information to answer this question based on the provided documents."
- Be concise but comprehensive in your responses
- Cite specific parts of the context when relevant
- If multiple documents contain relevant information, synthesize them into a coherent response
- When answering follow-up questions, maintain continuity with the previous conversation"""

_USER_TEMPLATE = """Context from user's documents:
{context}

Question: {question}

Answer:"""

prompt_template = PromptTemplate(
    input_variables=["context", "question"],
    template=_USER_TEMPLATE,
)

@functools.lru_cache()
def get_groq_client() -> Groq:
    """Initialize GROQ client with API key."""
    try:
        client = Groq(api_key=settings.GROQ_API_KEY)
        logger.info("GROQ client initialized successfully")
        return client
    except Exception as e:
        logger.error(f"Failed to initialize GROQ client: {e}")
        raise

def generate_response(
    context: str, 
    question: str,
    user_id: Optional[str] = None,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None
) -> Dict[str, Any]:
    """
    Generate a response using GROQ LLM with the provided context.
    
    Args:
        context: Document context for the question
        question: User's question
        user_id: User ID for logging purposes
        max_tokens: Maximum response tokens (defaults to config)
        temperature: Response randomness (defaults to config)
        
    Returns:
        Dictionary with response, metadata, and usage info
    """
    try:
        client = get_groq_client()
        
        # Format the prompt
        formatted_prompt = prompt_template.format(
            context=context,
            question=question
        )
        
        # Prepare request parameters
        request_params = {
            "model": settings.GROQ_MODEL,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": formatted_prompt}
            ],
            "max_tokens": max_tokens or settings.LLM_MAX_TOKENS,
            "temperature": temperature or settings.LLM_TEMPERATURE,
        }
        
        logger.info(f"Generating response for user {user_id} using {settings.GROQ_MODEL}")
        
        # Make the API call
        response = client.chat.completions.create(**request_params)
        
        # Extract response data
        answer = response.choices[0].message.content
        usage = response.usage
        
        result = {
            "answer": answer,
            "model": settings.GROQ_MODEL,
            "usage": {
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens
            },
            "metadata": {
                "user_id": user_id,
                "question": question,
                "context_length": len(context)
            }
        }
        
        logger.info(f"Response generated successfully for user {user_id}: {usage.total_tokens} tokens used")
        return result
        
    except Exception as e:
        logger.error(f"Failed to generate response for user {user_id}: {e}")
        raise


def generate_response_with_history(
    context: str,
    question: str,
    history: Optional[List[tuple[str, str]]] = None,
    user_id: Optional[str] = None,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None
) -> Dict[str, Any]:
    """
    Generate a response using GROQ LLM with full conversation history and context injection.
    """
    try:
        client = get_groq_client()

        # Start with system prompt
        messages = [{"role": "system", "content": _SYSTEM_PROMPT}]

        # Add historical conversation messages
        if history:
            for user_q, assistant_a in history:
                messages.append({"role": "user", "content": user_q})
                if assistant_a:
                    messages.append({"role": "assistant", "content": assistant_a})

        # Now add the latest user message with context
        user_message = f"""Context from user's documents:\n{context}\n\nQuestion: {question}"""
        messages.append({"role": "user", "content": user_message})

        request_params = {
            "model": settings.GROQ_MODEL,
            "messages": messages,
            "max_tokens": max_tokens or settings.LLM_MAX_TOKENS,
            "temperature": temperature or settings.LLM_TEMPERATURE,
        }

        logger.info(f"Generating response with history for user {user_id} using {settings.GROQ_MODEL}")

        response = client.chat.completions.create(**request_params)

        answer = response.choices[0].message.content
        usage = response.usage

        return {
            "answer": answer,
            "model": settings.GROQ_MODEL,
            "usage": {
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens
            },
            "metadata": {
                "user_id": user_id,
                "question": question,
                "context_length": len(context),
                "history_turns": len(history) if history else 0
            }
        }

    except Exception as e:
        logger.error(f"Failed to generate response with history for user {user_id}: {e}")
        raise


def format_context_from_documents(documents: List[Any]) -> str:
    """
    Format retrieved documents into context string for the LLM.
    
    Args:
        documents: List of Document objects with page_content and metadata
        
    Returns:
        Formatted context string
    """
    if not documents:
        return "No relevant documents found."
    
    context_parts = []
    for i, doc in enumerate(documents, 1):
        # Get filename from metadata if available
        filename = doc.metadata.get("filename", "Unknown")
        doc_id = doc.metadata.get("doc_id", "Unknown")
        
        context_parts.append(f"Document {i} (File: {filename}):\n{doc.page_content}")
    
    return "\n\n---\n\n".join(context_parts)

# Legacy function for backward compatibility
@functools.lru_cache()
def qa_chain():
    """
    Legacy QA chain function for backward compatibility.
    WARNING: This is deprecated. Use generate_response() instead.
    """
    logger.warning("Using deprecated qa_chain function!")
    
    class LegacyChain:
        def invoke(self, inputs: Dict[str, str]) -> Dict[str, str]:
            context = inputs.get("context", "")
            question = inputs.get("question", "")
            
            result = generate_response(context, question)
            return {"content": result["answer"]}
    
    return LegacyChain()

# Convenience function for backward compatibility
async def ask(question: str, context: str = "", history: Optional[List[tuple[str, str]]] = None) -> str:
    """
    Simple async wrapper for generating responses with history support.
    
    Args:
        question: User's question
        context: Document context
        history: Optional conversation history as (user, assistant) tuples
        
    Returns:
        Generated answer text
    """
    try:
        if history:
            result = generate_response_with_history(context, question, history)
        else:
            result = generate_response(context, question)
        
        return result["answer"]
    except Exception as e:
        logger.error(f"Failed to generate answer: {e}")
        return "I apologize, but I encountered an error while processing your question. Please try again."