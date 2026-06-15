from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from config import settings
import logging

logger = logging.getLogger("app.agents.llm")


def get_llm() -> BaseChatModel:
    """
    Initializes and returns the Chat LLM based on environment configuration.
    Falls back to a mock local chat model if no API keys are present.
    """
    if settings.GOOGLE_API_KEY:
        try:
            logger.info("Initializing ChatGoogleGenerativeAI...")
            return ChatGoogleGenerativeAI(
                model=settings.DEFAULT_LLM_MODEL,
                google_api_key=settings.GOOGLE_API_KEY,
                temperature=0.2,
            )
        except Exception as e:
            logger.error(f"Failed to initialize Gemini LLM: {e}. Falling back...")

    # Fallback / Local development mock chat model
    class MockChatModel(BaseChatModel):
        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            from langchain_core.outputs import ChatGeneration, ChatResult
            from langchain_core.messages import AIMessage

            last_msg = messages[-1].content.lower() if messages else ""

            # Simple keyword-based mocked agent routing/answers
            if (
                "arbitration" in last_msg
                or "analyze" in last_msg
                or "claim" in last_msg
            ):
                reply = "Routing to Arbitration Agent: Analysing legal rules..."
            elif "draft" in last_msg or "complaint" in last_msg or "pdf" in last_msg:
                reply = "Routing to Drafting Agent: Merging template variables..."
            elif "file" in last_msg or "submit" in last_msg:
                reply = "Routing to E-Filing Agent: Starting background workflow..."
            else:
                reply = "How can LxwyerUp help you today? You can analyze a case, draft complaints, or e-file claims."

            ai_msg = AIMessage(content=reply)
            return ChatResult(generations=[ChatGeneration(message=ai_msg)])

        @property
        def _llm_type(self) -> str:
            return "mock-chat"

    logger.warning("No Gemini API Key found. Using local MockChatModel.")
    return MockChatModel()
