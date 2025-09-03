# scripts/pinecone_crud_test_with_create.py
"""
Pinecone CRUD test script that will create the index if it does not exist.

Usage:
    python scripts/pinecone_crud_test_with_create.py

Notes:
 - It tries to reuse your `services.pinecone_service.index` and `config.settings`.
 - If those imports fail it will look for env vars:
     PINECONE_API_KEY, PINECONE_INDEX_NAME
 - Default dimension/metric are set to 1024 / cosine to match your screenshot.
"""

import logging
import os
import time
import uuid
import sys
from typing import List, Dict, Any

# logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(message)s")
logger = logging.getLogger("pinecone_crud_test")

# Try to import your settings and existing index
index = None
settings = None
try:
    from services.pinecone_service import index as imported_index, get_embedding as imported_get_embedding
    index = imported_index
    get_embedding = imported_get_embedding
    logger.info("Using index & get_embedding from services.pinecone_service")
except Exception:
    # If not available, we'll build Pinecone client from config or env vars below
    logger.info("services.pinecone_service import failed; will try to create/check index from Pinecone client.")
    try:
        from config import settings as config_settings
        settings = config_settings
        logger.info("Imported config.settings")
    except Exception:
        # fallback to environment variables
        settings = None
        logger.info("config.settings import failed; will look for env vars PINECONE_API_KEY and PINECONE_INDEX_NAME")

# If get_embedding not set by import, provide a lightweight deterministic embedding for tests.
if "get_embedding" not in globals():
    def get_embedding(text: str) -> List[float]:
        # deterministic pseudo-embedding for testing (length 1024 -> mostly zeros)
        # keep small non-zero values so Pinecone accepts it, but it's cheap.
        base = [float((ord(c) % 10) / 10.0) for c in (text or "")[:8]]
        return (base + [0.0] * 1024)[:1024]

# Helper: load credentials
def load_credentials():
    api_key = None
    index_name = None
    if settings is not None:
        api_key = getattr(settings, "pinecone_api_key", None)
        index_name = getattr(settings, "pinecone_index_name", None)
    if not api_key:
        api_key = os.getenv("PINECONE_API_KEY")
    if not index_name:
        index_name = os.getenv("PINECONE_INDEX_NAME")
    return api_key, index_name

# Ensure pinecone client and index exist
def ensure_index_exists(index_name: str, api_key: str, dimension: int = 1024, metric: str = "cosine"):
    """
    Ensures the index exists. Returns an index object (pc.Index(...)).
    Attempts to create the index if it does not exist.
    """
    if not api_key or not index_name:
        raise RuntimeError("Pinecone API key or index name missing. Provide via config.settings or env vars.")

    try:
        from pinecone import Pinecone
    except Exception as e:
        logger.error("Unable to import Pinecone client library: %s", e)
        raise

    pc = Pinecone(api_key=api_key)
    logger.info("Initialized Pinecone client")

    # Try to instantiate index object
    try:
        idx = pc.Index(index_name)
        # Try to call a lightweight describe to confirm
        try:
            # different SDKs expose different methods; try common ones
            if hasattr(idx, "describe_index_stats"):
                stats = idx.describe_index_stats()
            elif hasattr(pc, "describe_index"):
                # some wrappers expose index describe on client
                stats = pc.describe_index(index_name)
            else:
                stats = None
            logger.info("Index '%s' exists (describe call ok).", index_name)
            return idx
        except Exception as e:
            # If describe failed, check if it's a NotFound-like error
            logger.warning("Index describe failed for '%s': %s", index_name, e)
            # fallthrough to creation attempt
    except Exception as e:
        logger.info("Index object instantiation returned error (will attempt creation): %s", e)

    # Check list of indexes if possible
    try:
        if hasattr(pc, "list_indexes"):
            existing = pc.list_indexes()
        elif hasattr(pc, "indexes"):
            existing = pc.indexes()
        else:
            existing = None
    except Exception as e:
        logger.warning("Could not list indexes: %s", e)
        existing = None

    if existing and index_name in existing:
        logger.info("Index '%s' found in index list. Instantiating.", index_name)
        return pc.Index(index_name)

    # Attempt to create index
    try:
        logger.info("Creating index '%s' with dimension=%s metric=%s", index_name, dimension, metric)
        # Many Pinecone SDKs expose create_index on the client:
        if hasattr(pc, "create_index"):
            # some clients require a dict or named args
            try:
                pc.create_index(name=index_name, dimension=dimension, metric=metric)
            except TypeError:
                # try alternative signature
                pc.create_index(index_name, dimension, metric)
        else:
            raise RuntimeError("Pinecone client has no create_index method; cannot create index programmatically.")
        # wait a bit for index to become available in some deployments
        logger.info("Create index requested; sleeping 2s to allow provisioning")
        time.sleep(2)
        idx = pc.Index(index_name)
        # try a describe
        try:
            if hasattr(idx, "describe_index_stats"):
                idx.describe_index_stats()
            logger.info("Index '%s' created and ready.", index_name)
            return idx
        except Exception:
            logger.info("Index created but describe call failed; returning index object anyway.")
            return idx
    except Exception as e:
        logger.error("Failed to create index programmatically: %s", e)
        raise RuntimeError(f"Failed to create or access Pinecone index '{index_name}': {e}")

# Simple wrappers for CRUD operations (similar to previous script)
def create_vectors(index, texts: List[str], metadata_base: Dict[str, Any] = None) -> List[str]:
    if index is None:
        raise RuntimeError("Index is None")
    metadata_base = metadata_base or {}
    vectors = []
    ids = []
    for i, txt in enumerate(texts):
        vec = get_embedding(txt)
        vid = f"test_{int(time.time())}_{uuid.uuid4().hex[:8]}_{i}"
        meta = metadata_base.copy()
        meta.update({"original_text": txt, "test_run": True, "created_at": int(time.time()), "chunk_index": i})
        vectors.append({"id": vid, "values": vec, "metadata": meta})
        ids.append(vid)
    logger.info("Upserting %d vectors", len(vectors))
    resp = index.upsert(vectors)
    logger.info("Upsert response: %s", resp)
    return ids

def fetch_by_id(index, ids: List[str]):
    logger.info("Fetching ids: %s", ids)
    return index.fetch(ids=ids)

def query_similar(index, text: str, top_k: int = 3, filter: Dict = None):
    emb = get_embedding(text)
    resp = index.query(vector=emb, top_k=top_k, include_metadata=True, filter=filter or {})
    # normalize response to dict-of-matches if necessary
    if isinstance(resp, dict):
        return resp.get("matches", [])
    else:
        # some clients return an object with .matches
        return getattr(resp, "matches", []) or []

def update_vector_metadata(index, vector_id: str, new_metadata: Dict[str, Any]):
    # best-effort: fetch current vector values
    fetched = fetch_by_id(index, [vector_id])
    values = None
    try:
        vectors = fetched.get("vectors", {})
        values = vectors.get(vector_id, {}).get("values")
    except Exception:
        pass
    if not values:
        logger.warning("Could not fetch values for %s; embedding placeholder text", vector_id)
        values = get_embedding(str(new_metadata.get("original_text", "updated_vector")))
    resp = index.upsert([{"id": vector_id, "values": values, "metadata": new_metadata}])
    logger.info("Update response: %s", resp)
    return resp

def delete_vectors(index, ids: List[str] = None, delete_filter: Dict = None):
    if ids:
        resp = index.delete(ids=ids)
    elif delete_filter:
        resp = index.delete(filter=delete_filter)
    else:
        raise ValueError("Provide ids or delete_filter")
    logger.info("Delete response: %s", resp)
    return resp

# Main sequence combining ensure_index_exists + CRUD
def run_sequence():
    api_key, index_name = load_credentials()
    if not api_key or not index_name:
        logger.error("Missing Pinecone credentials. Provide via config.settings or env vars.")
        logger.error("Tried settings.pinecone_api_key / settings.pinecone_index_name and env vars PINECONE_API_KEY / PINECONE_INDEX_NAME")
        sys.exit(1)

    try:
        idx = ensure_index_exists(index_name=index_name, api_key=api_key, dimension=1024, metric="cosine")
    except Exception as e:
        logger.exception("Could not ensure index exists: %s", e)
        sys.exit(1)

    # proceed with CRUD test
    texts = [
        "Hi there my name is Sahil Thakur.",
        "I live in new Delhi.",
        "I Usually do my work from Home."
    ]
    created_ids = create_vectors(idx, texts, metadata_base={"user_id": 123, "source": "crud_test"})
    print("CREATE: OK", created_ids)

    time.sleep(1)

    # fetch
    fresp = fetch_by_id(idx, [created_ids[0]])
    print(f"Found the context---> {fresp}")
    found = False
    try:
        if isinstance(fresp, dict):
            found = bool(fresp.get("vectors"))
        else:
            # try object form
            found = bool(getattr(fresp, "vectors", None))
    except Exception:
        found = False
    print("FETCH_BY_ID:", "OK" if found else "FAIL")

    # query
    matches = query_similar(idx, "talk about oranges", top_k=3, filter={"user_id": {"$eq": 123}})
    print("QUERY_SIMILAR:", "OK" if matches else "FAIL")

    # update metadata
    try:
        update_vector_metadata(idx, created_ids[0], {"user_id": 123, "updated": True, "note": "updated by test"})
        print("UPDATE_METADATA: OK")
    except Exception:
        print("UPDATE_METADATA: FAIL")

    # delete one
    # delete_vectors(idx, ids=[created_ids[1]])
    # print("DELETE_ONE: requested")

    # cleanup remaining
    try:
        remaining = [i for i in created_ids if i != created_ids[1]]
        # delete_vectors(idx, ids=remaining)
        # print("CLEANUP: OK")
    except Exception:
        print("CLEANUP: FAIL")

if __name__ == "__main__":
    logger.info("Starting Pinecone CRUD test sequence (with ensure-index)")
    run_sequence()
    logger.info("Completed")
