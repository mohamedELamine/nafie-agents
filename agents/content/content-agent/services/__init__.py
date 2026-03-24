from importlib import import_module

_EXPORTS = {
    "ClaudeContentClient": ".claude_client",
    "RedisBus": ".redis_bus",
    "ContentResendClient": ".resend_client",
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
