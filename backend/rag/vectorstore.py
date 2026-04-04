from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from rag.loader import load_and_split_documents

_vectorstore: FAISS | None = None


def get_embeddings():
    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
    )


def get_vectorstore() -> FAISS:
    global _vectorstore
    if _vectorstore is None:
        chunks = load_and_split_documents()
        embeddings = get_embeddings()
        _vectorstore = FAISS.from_documents(chunks, embeddings)
    return _vectorstore


def retrieve(query: str, k: int = 3) -> list[str]:
    vs = get_vectorstore()
    docs = vs.similarity_search(query, k=k)
    return [doc.page_content for doc in docs]
