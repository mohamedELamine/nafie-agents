#!/usr/bin/env python3
"""Seed Qdrant with support knowledge documents."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import uuid
from pathlib import Path
from typing import Any

from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

try:
    from logging_config import get_logger  # type: ignore
except ImportError:  # pragma: no cover - optional project logger
    get_logger = None


logger = (
    get_logger("scripts.seed_qdrant")
    if callable(get_logger)
    else logging.getLogger("scripts.seed_qdrant")
)

COLLECTION_NAME = "support_knowledge"
DEFAULT_VECTOR_SIZE = 1536


def configure_logging() -> None:
    if callable(get_logger):
        return
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")


def default_documents() -> list[dict[str, str]]:
    topics = [
        ("install-wordpress-theme", "كيفية تثبيت قالب WordPress", "يمكن تثبيت القالب من لوحة التحكم عبر المظهر ثم القوالب ثم رفع ملف ZIP وتفعيله."),
        ("activate-license", "كيفية تفعيل الترخيص عبر Lemon Squeezy", "افتح إعدادات القالب وأدخل مفتاح الترخيص الذي وصلك بعد الشراء من Lemon Squeezy ثم احفظ التغييرات."),
        ("faq-updates", "الأسئلة الشائعة عن التحديثات", "التحديثات متاحة طوال فترة الترخيص الفعّال ويمكن تثبيتها من لوحة التحكم أو يدويًا عبر ZIP."),
        ("faq-support", "الأسئلة الشائعة عن الدعم", "يشمل الدعم المساعدة في التثبيت والإعداد الأساسي ومشاكل التوافق الشائعة."),
        ("refund-policy", "سياسة الاسترداد", "يمكن طلب الاسترداد خلال المدة المحددة في سياسة المنتج إذا كان القالب لا يعمل كما هو موضح."),
        ("compatibility-plugins", "خطوات حل مشاكل التوافق مع الإضافات", "عطّل الإضافات المتعارضة بالتتابع ثم اختبر القالب مع أحدث نسخة من WordPress وWooCommerce."),
        ("compatibility-cache", "خطوات حل مشاكل الكاش", "امسح كاش المتصفح وكاش الموقع وأعد تحميل الملفات الثابتة بعد أي تحديث للقالب."),
        ("import-demo", "كيفية استيراد المحتوى التجريبي", "استخدم أداة الاستيراد المرفقة داخل القالب أو اتبع ملف الإرشادات لاستيراد الصفحات والقوائم."),
        ("troubleshoot-style", "حل مشاكل التنسيق بعد التحديث", "تحقق من الـ custom CSS والإضافات التي تعدل الواجهة ثم أعد حفظ إعدادات القالب."),
        ("theme-requirements", "متطلبات تشغيل القالب", "يوصى باستخدام آخر إصدار مستقر من WordPress وPHP 8.1 أو أحدث مع WooCommerce المدعوم."),
    ]
    return [
        make_document(doc_id, title, text, Path("default_examples"))
        for doc_id, title, text in topics
    ]


def load_documents(base_dir: Path) -> list[dict[str, str]]:
    if not base_dir.exists():
        return default_documents()

    docs: list[dict[str, str]] = []
    for path in sorted(base_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".md", ".txt", ".json"}:
            continue
        if path.suffix.lower() == ".json":
            docs.extend(load_json_documents(path))
            continue
        text = path.read_text(encoding="utf-8").strip()
        if text:
            docs.append(make_document(path.stem, path.stem.replace("-", " "), text, path))
    return docs or default_documents()


def load_json_documents(path: Path) -> list[dict[str, str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    items = payload if isinstance(payload, list) else [payload]
    docs: list[dict[str, str]] = []
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or f"{path.stem}-{index}")
        text = str(item.get("text") or item.get("content") or "").strip()
        if text:
            docs.append(
                make_document(str(item.get("id") or f"{path.stem}-{index}"), title, text, path)
            )
    return docs


def make_document(doc_id: str, title: str, text: str, source: Path) -> dict[str, str]:
    stable_id = str(uuid.uuid5(uuid.NAMESPACE_URL, doc_id))
    return {"id": stable_id, "title": title, "text": text, "source": str(source)}


def make_openai_client() -> OpenAI | None:
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.warning("No embedding API key found; using deterministic fallback embeddings")
        return None
    base_url = os.getenv("SUPPORT_EMBEDDING_BASE_URL")
    kwargs = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url
    return OpenAI(**kwargs)


def normalize_vector(vector: list[float], vector_size: int) -> list[float]:
    if len(vector) == vector_size:
        return vector
    if len(vector) > vector_size:
        return vector[:vector_size]
    return vector + [0.0] * (vector_size - len(vector))


def embed_text(client: OpenAI | None, model: str, text: str, vector_size: int) -> list[float]:
    if client is None:
        seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest(), 16)
        return [((seed >> (i % 32)) & 0xFF) / 255.0 for i in range(vector_size)]
    response = client.embeddings.create(model=model, input=text)
    vector = list(response.data[0].embedding)
    return normalize_vector(vector, vector_size)


def ensure_collection(client: QdrantClient, vector_size: int) -> None:
    if client.collection_exists(COLLECTION_NAME):
        return
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
    )
    logger.info("Created Qdrant collection %s", COLLECTION_NAME)


def seed_documents(
    client: QdrantClient,
    embedding_client: OpenAI | None,
    documents: list[dict[str, str]],
    model: str,
    vector_size: int,
) -> int:
    inserted = 0
    for doc in documents:
        if client.retrieve(COLLECTION_NAME, ids=[doc["id"]], with_payload=False):
            continue
        vector = embed_text(embedding_client, model, doc["text"], vector_size)
        point = PointStruct(
            id=doc["id"],
            vector=vector,
            payload={
                "title": doc["title"],
                "text": doc["text"],
                "source": doc["source"],
            },
        )
        client.upsert(collection_name=COLLECTION_NAME, points=[point])
        inserted += 1
    return inserted


def main() -> int:
    configure_logging()
    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    model = os.getenv("SUPPORT_EMBEDDING_MODEL", "text-embedding-3-small")
    vector_size = int(os.getenv("SUPPORT_EMBEDDING_VECTOR_SIZE", str(DEFAULT_VECTOR_SIZE)))
    client = QdrantClient(url=qdrant_url)
    embedding_client = make_openai_client()
    ensure_collection(client, vector_size)
    docs = load_documents(Path("knowledge_base"))
    inserted = seed_documents(client, embedding_client, docs, model, vector_size)
    print(f"collection={COLLECTION_NAME}")
    print(f"vector_size={vector_size}")
    print(f"inserted_documents={inserted}")
    print(f"total_documents={len(docs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
