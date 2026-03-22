"""
FastAPI App — وكيل المنصة
TODO: تنفيذ كامل (راجع tasks/phase5_commerce_consumer.md § T080–T085)
"""
from fastapi import FastAPI, Request, Header, HTTPException
from ..commerce import CommerceEventConsumer

app = FastAPI(title="Platform Agent API")
consumer = CommerceEventConsumer()


@app.post("/webhooks/lemonsqueezy")
async def lemonsqueezy_webhook(
    request: Request,
    x_signature: str = Header(None, alias="X-Signature")
):
    """TODO: T080 — استقبال Webhooks من Lemon Squeezy"""
    raise NotImplementedError("TODO: T080")


@app.get("/health")
async def health():
    return {"status": "ok", "agent": "platform"}
