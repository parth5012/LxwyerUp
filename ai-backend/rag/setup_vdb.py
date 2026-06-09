from langchain_chroma.vectorstores import Chroma
from rag.embeddings import embedding

vdb = Chroma(collection_name='Judgements',embedding_function=embedding)