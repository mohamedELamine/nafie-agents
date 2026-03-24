from importlib import import_module

_EXPORTS = {
    "FacebookClient": ".facebook_client",
    "get_facebook_client": ".facebook_client",
    "InstagramClient": ".instagram_client",
    "get_instagram_client": ".instagram_client",
    "TikTokClient": ".tiktok_client",
    "get_tiktok_client": ".tiktok_client",
    "WhatsAppClient": ".whatsapp_client",
    "get_whatsapp_client": ".whatsapp_client",
    "RedisBus": ".redis_bus",
    "get_redis_bus": ".redis_bus",
    "ResendClient": ".resend_client",
    "send_campaign_launched": ".resend_client",
    "send_publish_failed": ".resend_client",
    "send_paid_channel_suggestion": ".resend_client",
}

__all__ = list(_EXPORTS)


def __getattr__(name: str):
    module_name = _EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module = import_module(module_name, __name__)
    value = getattr(module, name)
    globals()[name] = value
    return value
