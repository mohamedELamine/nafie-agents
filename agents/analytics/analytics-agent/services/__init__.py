from importlib import import_module

_EXPORTS = {
    "LemonSqueezyClient": ".lemon_squeezy_client",
    "get_orders": ".lemon_squeezy_client",
    "HelpScoutClient": ".helpscout_client",
    "get_conversations": ".helpscout_client",
    "RedisBus": ".redis_bus",
    "get_redis_bus": ".redis_bus",
    "ResendClient": ".resend_client",
    "send_owner_alert": ".resend_client",
    "send_weekly_report": ".resend_client",
    "get_all_published_slugs": ".product_registry",
    "get_launch_date": ".product_registry",
    "get_product_activity_summary": ".product_registry",
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
