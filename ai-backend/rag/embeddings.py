from langchain_google_genai.embeddings import GoogleGenerativeAIEmbeddings
from config import settings

embedding = GoogleGenerativeAIEmbeddings(
    model=settings.EMBEDDING_MODEL, api_key=settings.GOOGLE_API_KEY
)
