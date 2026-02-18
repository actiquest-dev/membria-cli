"""Knowledge Base ingestion: parse files, chunk, embed, store in graph."""

import hashlib
import logging
import os
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from membria.graph import GraphClient
from membria.graph_schema import DocumentNodeSchema
from membria.md_xtract import xtract_to_markdown
from membria.security import sanitize_text


logger = logging.getLogger(__name__)

DEFAULT_EXTENSIONS = {".md", ".txt", ".pdf", ".docx", ".pptx", ".xlsx", ".html", ".htm", ".png", ".jpg", ".jpeg"}


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> List[str]:
    if chunk_size <= 0:
        return [text]
    if overlap >= chunk_size:
        overlap = max(0, chunk_size // 4)
    chunks = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = min(text_len, start + chunk_size)
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap
        if start < 0:
            start = 0
        if end == text_len:
            break
    return chunks


def cohere_embed(
    texts: List[str],
    api_key: str,
    model: str = "embed-english-light-v3.0",
    input_type: str = "search_document",
) -> List[List[float]]:
    if not api_key:
        raise RuntimeError("COHERE_API_KEY is required for embeddings.")

    url = "https://api.cohere.ai/v1/embed"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-Client-Name": "membria-cli",
    }
    payload = {
        "texts": texts,
        "model": model,
        "input_type": input_type,
    }

    with httpx.Client(timeout=60) as client:
        resp = client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        embeddings = data.get("embeddings") or data.get("embeddings_floats")
        if not embeddings:
            raise RuntimeError("Cohere response missing embeddings.")
        return embeddings


def _batched(items: List[str], batch_size: int = 96) -> Iterable[List[str]]:
    for i in range(0, len(items), batch_size):
        yield items[i : i + batch_size]


def ingest_documents(
    root: str,
    graph_client: GraphClient,
    api_key: str,
    doc_type: str = "kb",
    tags: Optional[List[str]] = None,
    extensions: Optional[Iterable[str]] = None,
    chunk_size: int = 800,
    overlap: int = 100,
    model: str = "embed-english-light-v3.0",
    strict: bool = False,
) -> Dict[str, int]:
    root_path = Path(root).expanduser().resolve()
    if not root_path.exists():
        raise FileNotFoundError(f"Path not found: {root_path}")

    exts = set(e.lower() for e in (extensions or DEFAULT_EXTENSIONS))
    files = []
    if root_path.is_file():
        files = [root_path]
    else:
        for p in root_path.rglob("*"):
            if p.is_file() and p.suffix.lower() in exts:
                files.append(p)

    if not files:
        return {"files": 0, "chunks": 0}

    all_chunks: List[Tuple[Path, str, int, int]] = []
    skipped = 0
    for path in files:
        try:
            text, _ = xtract_to_markdown(str(path))
        except Exception as e:
            skipped += 1
            if strict:
                raise
            logger.warning("MD xtract failed for %s: %s", path, e)
            continue
        text = sanitize_text(text, max_len=0)  # sanitize control chars, no truncation
        chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)
        total = len(chunks)
        for idx, chunk in enumerate(chunks):
            all_chunks.append((path, chunk, idx, total))

    # Embed in batches
    embeddings: List[List[float]] = []
    texts = [c[1] for c in all_chunks]
    for batch in _batched(texts, batch_size=96):
        embeddings.extend(cohere_embed(batch, api_key=api_key, model=model))

    # Store in graph
    now_ts = int(__import__("time").time())
    for (path, chunk, idx, total), emb in zip(all_chunks, embeddings):
        doc_id = _make_doc_id(path, idx)
        metadata = {
            "chunk_index": idx,
            "chunk_total": total,
            "tags": tags or [],
        }
        doc = DocumentNodeSchema(
            id=doc_id,
            file_path=str(path),
            content=chunk,
            doc_type=doc_type,
            created_at=now_ts,
            updated_at=now_ts,
            embedding=emb,
            metadata=metadata,
        )
        cypher = doc.to_cypher_create()
        graph_client.query(cypher)

    return {"files": len(files), "chunks": len(all_chunks), "skipped": skipped}


def _make_doc_id(path: Path, chunk_idx: int) -> str:
    h = hashlib.sha1(str(path).encode("utf-8")).hexdigest()[:10]
    return f"doc_{h}_{chunk_idx}"
