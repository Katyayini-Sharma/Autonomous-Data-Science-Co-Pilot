import os

# from langchain_core.documents import Document
# from langchain_text_splitters import RecursiveCharacterTextSplitter
# from langchain_huggingface import HuggingFaceEmbeddings
# from langchain_community.vectorstores import FAISS

KB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "knowledge_base", "docs")
VECTORSTORE_CACHE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".vectorstore_cache")

_EMBEDDINGS = None
_VECTORSTORE = None


def _get_embeddings():
    global _EMBEDDINGS
    if _EMBEDDINGS is None:
        from langchain_huggingface import HuggingFaceEmbeddings
        _EMBEDDINGS = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    return _EMBEDDINGS


def _load_docs():
    from langchain_core.documents import Document
    docs = []
    for fname in sorted(os.listdir(KB_DIR)):
        if not fname.endswith(".md"):
            continue
        with open(os.path.join(KB_DIR, fname), "r", encoding="utf-8") as f:
            docs.append(Document(page_content=f.read(), metadata={"source": fname}))
    return docs


def build_or_load_vectorstore(force_rebuild: bool = False):
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_community.vectorstores import FAISS
    global _VECTORSTORE
    if _VECTORSTORE is not None and not force_rebuild:
        return _VECTORSTORE

    embeddings = _get_embeddings()

    if os.path.isdir(VECTORSTORE_CACHE) and not force_rebuild:
        try:
            _VECTORSTORE = FAISS.load_local(VECTORSTORE_CACHE, embeddings, allow_dangerous_deserialization=True)
            return _VECTORSTORE
        except Exception:
            pass

    raw_docs = _load_docs()
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
    chunks = splitter.split_documents(raw_docs)

    _VECTORSTORE = FAISS.from_documents(chunks, embeddings)
    os.makedirs(VECTORSTORE_CACHE, exist_ok=True)
    _VECTORSTORE.save_local(VECTORSTORE_CACHE)
    return _VECTORSTORE


def retrieve_fix_context(error_message: str, k: int = 2) -> str:
    vectorstore = build_or_load_vectorstore()

    # Pull out the exception type name (e.g. "KeyError") from a standard
    # Python error message, formatted like "KeyError: 'revenue'".
    error_type = error_message.split(":")[0].strip() if ":" in error_message else ""

    # Over-fetch semantic candidates, dedupe to one chunk per source file.
    raw_results = vectorstore.similarity_search(error_message, k=k * 4)
    seen_sources = set()
    candidates = []
    for doc in raw_results:
        source = doc.metadata.get("source", "unknown")
        if source in seen_sources:
            continue
        seen_sources.add(source)
        candidates.append(doc)

    # Hybrid step: rerank so any document that literally mentions the exact
    # error type name (e.g. "KeyError") is prioritized over pure embedding
    # similarity. This corrects for the embedding model's weak performance
    # on short, code-heavy technical text (verified empirically -- see
    # README's Design Decisions section).
    if error_type:
        candidates.sort(key=lambda d: error_type in d.page_content, reverse=True)

    results = candidates[:k]

    if not results:
        return "No specific documentation match found — rely on general Python/pandas best practices."

    formatted = []
    for doc in results:
        source = doc.metadata.get("source", "unknown")
        formatted.append(f"[Reference: {source}]\n{doc.page_content.strip()}")
    return "\n\n---\n\n".join(formatted)