from __future__ import annotations

import os
from typing import Dict, List, Optional

import chromadb
from chromadb import Collection, PersistentClient

from src.config.settings import Config


# pyrefly: ignore [unsupported-operation]
_client: PersistentClient | None = None


# pyrefly: ignore [not-a-type]
def get_chroma_client(path: Optional[str] = None) -> PersistentClient:
    global _client
    if _client is None:
        db_path = path or Config.CHROMADB_PATH
        os.makedirs(db_path, exist_ok=True)
        _client = chromadb.PersistentClient(path=db_path)
    return _client


def get_or_create_collection(name: str, metadata: Optional[Dict[str, str]] = None) -> Collection:
    client = get_chroma_client()
    return client.get_or_create_collection(name, metadata=metadata)


def list_collections() -> List[str]:
    client = get_chroma_client()
    collections = client.list_collections()
    return [c.name for c in collections]