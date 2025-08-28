# routes/health.py
from sqlalchemy import text
from typing import Dict, Any
from time import perf_counter
from logger_config import logger
from fastapi import APIRouter, Query

router = APIRouter()

@router.get("/health")
async def health(
    include_db: bool = Query(True, description="Check database connectivity"),
    include_pinecone: bool = Query(True, description="Check Pinecone connectivity"),
    include_llm: bool = Query(True, description="Check LLM/embedding connectivity (may incur API call)")
) -> Dict[str, Any]:
    """
    Health endpoint that checks DB, Pinecone, and LLM connectivity.
    Query params:
      - include_db (bool): whether to check DB
      - include_pinecone (bool): whether to check Pinecone
      - include_llm (bool): whether to check LLM (embedding) — may call external API
    """
    logger.info("GET /health called (db=%s, pinecone=%s, llm=%s)", include_db, include_pinecone, include_llm)

    results: Dict[str, Any] = {
        "status": "ok",
        "components": {}
    }

    # 1) DB check
    if include_db:
        start = perf_counter()
        try:
            # Try to import DB engine/session directly to avoid side-effects
            from db.database import engine
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            elapsed = perf_counter() - start
            results["components"]["database"] = {"ok": True, "message": "DB connected", "latency_s": round(elapsed, 3)}
        except Exception as e:
            elapsed = perf_counter() - start
            logger.exception("DB health check failed: %s", e)
            results["components"]["database"] = {
                "ok": False,
                "message": f"DB error: {e}",
                "latency_s": round(elapsed, 3)
            }
            results["status"] = "degraded"

    # 2) Pinecone check
    if include_pinecone:
        start = perf_counter()
        try:
            # Prefer the small service wrapper if present
            try:
                from services.pinecone_client import describe_index_stats
                stats = describe_index_stats()
                # keep compact useful fields if present
                total = None
                if isinstance(stats, dict):
                    total = stats.get("total_vector_count") or (stats.get("describe_index_stats") or {}).get("total_vector_count")
                elapsed = perf_counter() - start
                results["components"]["pinecone"] = {
                    "ok": True,
                    "message": "Pinecone reachable",
                    "latency_s": round(elapsed, 3),
                    "total_vector_count": total
                }
            except Exception:
                # fallback: try to use services.pinecone_service.index.describe_index_stats()
                from services.pinecone_service import index as pc_index
                stats = pc_index.describe_index_stats()
                elapsed = perf_counter() - start
                # try to normalize
                total = None
                if isinstance(stats, dict):
                    total = stats.get("total_vector_count")
                results["components"]["pinecone"] = {
                    "ok": True,
                    "message": "Pinecone reachable (fallback)",
                    "latency_s": round(elapsed, 3),
                    "total_vector_count": total
                }
        except Exception as e:
            elapsed = perf_counter() - start
            logger.exception("Pinecone health check failed: %s", e)
            results["components"]["pinecone"] = {
                "ok": False,
                "message": f"Pinecone error: {e}",
                "latency_s": round(elapsed, 3)
            }
            results["status"] = "degraded"

    # 3) LLM / embedding check (optional)
    if include_llm:
        start = perf_counter()
        try:
            # Use your existing embedding helper which centralizes model choice
            from services.pinecone_service import get_embedding, EMBEDDING_MODEL
            # small test string (cheap)
            emb = get_embedding("health-check")
            elapsed = perf_counter() - start
            emb_len = len(emb) if emb is not None else None
            ok = bool(emb_len and emb_len > 0)
            results["components"]["llm"] = {
                "ok": ok,
                "message": "Embedding produced" if ok else "Embedding empty",
                "latency_s": round(elapsed, 3),
                "embedding_length": emb_len,
                "embedding_model": EMBEDDING_MODEL
            }
            if not ok:
                results["status"] = "degraded"
        except Exception as e:
            elapsed = perf_counter() - start
            logger.exception("LLM/embedding health check failed: %s", e)
            results["components"]["llm"] = {
                "ok": False,
                "message": f"LLM/embedding error: {e}",
                "latency_s": round(elapsed, 3)
            }
            results["status"] = "degraded"

    # Final status: if any component false -> 503
    status_code = 200 if results["status"] == "ok" else 503
    return results
