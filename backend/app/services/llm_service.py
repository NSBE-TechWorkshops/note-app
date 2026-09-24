from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from app.core.config import settings

_MODEL = "gpt-4o-mini"

_llm = ChatOpenAI(openai_api_key=settings.openai_api_key, model=_MODEL)

_SYSTEM_PROMPT = (
    "You are a helpful study assistant. Answer the student's question using ONLY the "
    "provided context from their notes. If the context doesn't contain enough information, "
    "say so. Cite which source chunks you used."
)


def generate_answer(question: str, context_chunks: list[str]) -> tuple[str, str]:
    """Generate a RAG answer. Returns (answer_text, model_name)."""
    context = "\n\n---\n\n".join(f"[Chunk {i + 1}]\n{c}" for i, c in enumerate(context_chunks))
    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=f"Context:\n{context}\n\nQuestion: {question}"),
    ]
    response = _llm.invoke(messages)
    return response.content, _MODEL
