from pathlib import Path
from typing import List, Dict
from elyra_backend.config import settings

# Optional imports - chromadb may not be available on Python 3.14
# Fix for chromadb 0.3.x compatibility with Pydantic 2.x
# We need to patch pydantic BEFORE importing chromadb
try:
    import sys
    import pydantic
    # Patch BaseSettings for older chromadb versions that expect it in pydantic
    # Inject directly into module dict to avoid triggering the migration error
    try:
        from pydantic_settings import BaseSettings
        pydantic.__dict__['BaseSettings'] = BaseSettings
        sys.modules['pydantic'].__dict__['BaseSettings'] = BaseSettings
    except ImportError:
        pass
    
    # Now try to import chromadb
    # Import PersistentClient directly to bypass Settings validation issues in __init__
    from chromadb import PersistentClient
    from sentence_transformers import SentenceTransformer
    # Test if chromadb actually works by creating a temporary client
    import tempfile
    import os
    with tempfile.TemporaryDirectory() as tmpdir:
        test_client = PersistentClient(path=tmpdir)
        test_collection = test_client.get_or_create_collection("test")
        del test_collection
        del test_client
    CHROMADB_AVAILABLE = True
except (ImportError, Exception) as e:
    # Catch both ImportError and runtime errors (like Pydantic compatibility issues)
    CHROMADB_AVAILABLE = False
    chromadb = None
    SentenceTransformer = None
    _CHROMADB_ERROR = str(e)

class DocsVectorStore:
    def __init__(self):
        if not CHROMADB_AVAILABLE:
            raise ImportError(
                "ChromaDB is not available. This may be due to Python 3.14 compatibility issues. "
                "Please install manually: pip install chromadb==0.4.20 sentence-transformers>=2.2.0"
            )
        self.client = chromadb.PersistentClient(path=settings.CHROMA_DB_PATH)
        self.collection = self.client.get_or_create_collection("docs_embeddings")
        self.embedding_model = SentenceTransformer(settings.DOCS_EMBEDDING_MODEL)

    def index_docs(self) -> None:
        docs_root = Path("docs")
        if not docs_root.exists():
            raise ValueError("Documentation directory not found")

        chunks = []
        metadatas = []
        ids = []

        for path in docs_root.rglob("*.md"):
            try:
                text = path.read_text(encoding="utf-8")
                # Simple chunking by paragraphs
                file_chunks = [c.strip() for c in text.split("\n\n") if c.strip()]
                for i, chunk in enumerate(file_chunks):
                    chunks.append(chunk)
                    metadatas.append({
                        "path": str(path),
                        "chunk_index": i
                    })
                    ids.append(f"{path.stem}_{i}")
            except OSError as exc:
                raise RuntimeError(f"Documentation indexing failed for {path}: {exc}")

        if chunks:
            embeddings = self.embedding_model.encode(chunks).tolist()
            self.collection.add(
                documents=chunks,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        if self.collection.count() == 0:
            self.index_docs()

        query_embedding = self.embedding_model.encode([query]).tolist()[0]
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )

        formatted_results = []
        for i in range(len(results["ids"][0])):
            formatted_results.append({
                "path": results["metadatas"][0][i]["path"],
                "content": results["documents"][0][i],
                "chunk_index": results["metadatas"][0][i]["chunk_index"],
                "score": results["distances"][0][i],
                "source_reference": f"{results['metadatas'][0][i]['path']}#chunk-{results['metadatas'][0][i]['chunk_index']}"
            })

        return formatted_results
