"""
Tests for nodes/ticket_updater.py
"""
import importlib.util
import pathlib
import sys
import types
from unittest.mock import MagicMock


AGENT_ROOT = pathlib.Path(__file__).resolve().parents[1]
PROJECT_ROOT = AGENT_ROOT.parents[3]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _pkg(name: str, path: pathlib.Path, parent: types.ModuleType | None = None) -> types.ModuleType:
    module = types.ModuleType(name)
    module.__file__ = str(path / "__init__.py")
    module.__path__ = [str(path)]
    module.__package__ = name
    sys.modules[name] = module
    if parent is not None:
        setattr(parent, name.rsplit(".", 1)[-1], module)
    return module


def _load_module(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


support_agent = _pkg("support_agent", AGENT_ROOT)
support_nodes = _pkg("support_agent.nodes", AGENT_ROOT / "nodes", support_agent)

ticket_updater = _load_module(
    "support_agent.nodes.ticket_updater",
    AGENT_ROOT / "nodes" / "ticket_updater.py",
)
TicketUpdaterNode = ticket_updater.TicketUpdaterNode


def test_ticket_updater_replies_to_facebook_comments():
    helpscout = MagicMock()
    redis_bus = MagicMock()
    facebook = MagicMock()
    node = TicketUpdaterNode(helpscout, redis_bus, facebook)

    state = {
        "ticket": {
            "ticket_id": "comment_1",
            "platform": "facebook",
            "page_id": "page_123",
        },
        "support_answer": {
            "answer_text": "اهلا، تم الرد على تعليقك.",
            "confidence": 0.9,
            "sources": ["kb/facebook.md"],
        },
        "overall_risk_level": "low",
    }

    result = node(state)

    assert result["ticket"]["updated"] is True
    facebook.reply_comment.assert_called_once_with(
        comment_id="comment_1",
        message="اهلا، تم الرد على تعليقك.",
        page_id="page_123",
    )
    helpscout.reply.assert_not_called()
    redis_bus.publish_message.assert_called_once()


def test_ticket_updater_records_no_answer_without_crashing():
    helpscout = MagicMock()
    redis_bus = MagicMock()
    node = TicketUpdaterNode(helpscout, redis_bus)

    state = {
        "ticket": {
            "ticket_id": "ticket_42",
            "platform": "helpscout",
        },
        "support_answer": None,
        "overall_risk_level": "low",
    }

    result = node(state)

    assert result["ticket"]["ticket_id"] == "ticket_42"
    helpscout.add_note.assert_called_once()
    redis_bus.publish_message.assert_called_once()
