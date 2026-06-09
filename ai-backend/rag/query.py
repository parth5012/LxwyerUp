import numpy as np
from typing import List, Dict, Any
from config import settings
import logging

logger = logging.getLogger("app.rag")

# In-memory "Legal Ground Truth" arbitration clauses for mock/fallback
# LEGAL_GROUND_TRUTH = [
#     {
#         "id": 1,
#         "title": "Rule 1: Initiation of Arbitration",
#         "content": "Any party to a contract containing an arbitration clause referencing LxwyerUp Rules may initiate arbitration by filing a User Request with the LxwyerUp platform and serving the other party."
#     },
#     {
#         "id": 2,
#         "title": "Rule 2: Jurisdiction and Validity of Contract",
#         "content": "The arbitration tribunal shall have the power to rule on its own jurisdiction, including any objections with respect to the existence, scope, or validity of the arbitration agreement."
#     },
#     {
#         "id": 3,
#         "title": "Rule 3: Appointment of Arbitrator",
#         "content": "If the parties have not agreed on the number of arbitrators, a sole arbitrator shall be appointed by default within 14 days of filing the initiation request."
#     },
#     {
#         "id": 4,
#         "title": "Rule 4: Evidence Submission and Document Production",
#         "content": "Each party shall have the burden of proving the facts relied upon to support its claim or defense. Written evidence must be submitted to the S3 Evidence Storage repository before the preliminary hearing."
#     },
#     {
#         "id": 5,
#         "title": "Rule 5: Final and Binding Awards",
#         "content": "Awards shall be made in writing, stating the reasons upon which the award is based, and shall be final and binding on the parties from the date they are rendered."
#     }
# ]

LEGAL_GROUND_TRUTH =  []
def query_vector_db(query: str, limit: int = 2) -> List[Dict[str, Any]]:
    """
    Simulates a Vector Database query.
    If Gemini API key is configured, uses LangChain GoogleGenAIEmbeddings to query.
    Otherwise, uses term frequency-based matching over the legal ground truth clauses.
    """
    if not query or len(query.strip()) == 0:
        return []

    # If Gemini is configured, simulate embeddings-based retrieval
    if settings.GEMINI_API_KEY:
        try:
            from langchain_google_genai import GoogleGenAIEmbeddings
            embeddings = GoogleGenAIEmbeddings(model="models/embedding-001", google_api_key=settings.GEMINI_API_KEY)
            
            # Embed the query
            query_vector = np.array(embeddings.embed_query(query))
            
            # Embed the ground truths (normally cached or pre-indexed)
            scored_clauses = []
            for doc in LEGAL_GROUND_TRUTH:
                doc_vector = np.array(embeddings.embed_query(doc["content"]))
                
                # Cosine similarity
                dot_product = np.dot(query_vector, doc_vector)
                norm_q = np.linalg.norm(query_vector)
                norm_d = np.linalg.norm(doc_vector)
                similarity = dot_product / (norm_q * norm_d) if norm_q > 0 and norm_d > 0 else 0.0
                
                scored_clauses.append((similarity, doc))
                
            scored_clauses.sort(key=lambda x: x[0], reverse=True)
            return [item[1] for item in scored_clauses[:limit]]
        except Exception as e:
            logger.error(f"Error querying Gemini embeddings: {e}. Falling back to keyword search.")

    # Fallback keyword matching (TF-like scoring based on word intersection)
    query_words = set(query.lower().split())
    scored_clauses = []
    
    for doc in LEGAL_GROUND_TRUTH:
        doc_words = set(doc["content"].lower().split() + doc["title"].lower().split())
        score = len(query_words.intersection(doc_words))
        scored_clauses.append((score, doc))
        
    scored_clauses.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in scored_clauses[:limit]]
