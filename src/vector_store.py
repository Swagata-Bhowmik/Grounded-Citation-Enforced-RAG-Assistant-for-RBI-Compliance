"""
vector_store.py
===============
Stores the chunk embeddings in ChromaDB and retrieves them by similarity.

WHAT CHROMADB IS
----------------
ChromaDB is a small, open-source "vector database". A normal database finds rows
by exact values; a vector database finds items by *nearness in meaning space*.
We hand it our 384-dim chunk vectors once; afterwards it answers "which chunks
are closest to this query vector?" in milliseconds, and it PERSISTS to disk so
the index survives restarts (ours lives on D:).

WHY WE STORE OUR OWN EMBEDDINGS
-------------------------------
Chroma can embed text for us, but we pass in the vectors WE computed with
bge-small. That keeps one single embedding model across the whole system
(no silent mismatch between how chunks and queries are vectorised) and lets us
reuse the (1252 x 384) matrix from Section 5.

DISTANCE / SIMILARITY
---------------------
We create the collection with cosine space. Chroma returns a *distance*
(0 = identical). We convert to an intuitive similarity = 1 - distance, so higher
means more relevant, matching the demo in Section 5.
"""

from __future__ import annotations

import chromadb

COLLECTION_NAME = "rbi_compliance"


def get_client(chroma_dir: str) -> "chromadb.ClientAPI":
    """A persistent Chroma client rooted on disk (D:), so the index is durable."""
    return chromadb.PersistentClient(path=str(chroma_dir))


def build_collection(client, chunks: list[dict], embeddings, rebuild: bool = True):
    """
    Create (or reset) the collection and add every chunk with its vector,
    page-level metadata, and text. Returns the collection.
    """
    if rebuild:
        try:
            client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass  # nothing to delete on first run

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},   # nearest-neighbour by cosine distance
    )

    ids = [c["chunk_id"] for c in chunks]
    documents = [c["text"] for c in chunks]
    metadatas = [
        {
            "source_file": c["source_file"],
            "page": int(c["page"]),
            "token_count": int(c["token_count"]),
        }
        for c in chunks
    ]

    # Add in batches to keep memory flat and show progress on large corpora.
    batch = 256
    for start in range(0, len(ids), batch):
        end = start + batch
        collection.add(
            ids=ids[start:end],
            embeddings=[v.tolist() for v in embeddings[start:end]],
            documents=documents[start:end],
            metadatas=metadatas[start:end],
        )
    return collection


def search(collection, query_vector, k: int = 5) -> list[dict]:
    """
    Return the top-k chunks nearest to `query_vector`, each as a dict with
    text, source_file, page, and a similarity score (higher = more relevant).
    """
    res = collection.query(
        query_embeddings=[query_vector.tolist()],
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )
    hits = []
    for doc, meta, dist in zip(
        res["documents"][0], res["metadatas"][0], res["distances"][0]
    ):
        hits.append(
            {
                "text": doc,
                "source_file": meta["source_file"],
                "page": meta["page"],
                "similarity": round(1.0 - float(dist), 3),
            }
        )
    return hits
