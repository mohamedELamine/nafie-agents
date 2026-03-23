from .claude_client import (
    ClaudeClient,
    get_claude_client,
)

from .qdrant_client import (
    QdrantClient,
    get_qdrant_client,
)

from .helpscout_client import (
    HelpScoutClient,
    get_helpscout_client,
)

from .facebook_client import (
    FacebookClient,
    get_facebook_client,
)

from .redis_bus import (
    RedisBus,
    get_redis_bus,
)

from .resend_client import (
    ResendClient,
    send_escalation_alert,
    send_recurring_issue_alert,
)

__all__ = [
    # Claude
    "ClaudeClient",
    "get_claude_client",
    # Qdrant
    "QdrantClient",
    "get_qdrant_client",
    # HelpScout
    "HelpScoutClient",
    "get_helpscout_client",
    # Facebook
    "FacebookClient",
    "get_facebook_client",
    # Redis Bus
    "RedisBus",
    "get_redis_bus",
    # Resend
    "ResendClient",
    "send_escalation_alert",
    "send_recurring_issue_alert",
]
