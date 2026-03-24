"""
Tests for nodes/ticket_receiver.py — make_ticket_receiver_node()
"""
from datetime import datetime
from support_agent.nodes.ticket_receiver import make_ticket_receiver_node


class TestMakeTicketReceiverNode:
    """Tests for the factory function itself."""

    def test_returns_callable(self):
        node = make_ticket_receiver_node()
        assert callable(node)

    def test_multiple_calls_return_independent_functions(self):
        node_a = make_ticket_receiver_node()
        node_b = make_ticket_receiver_node()
        assert node_a is not node_b


class TestTicketReceiverNode:
    """Tests for the inner ticket_receiver_node function."""

    def setup_method(self):
        self.node = make_ticket_receiver_node()

    # ── Happy path ──────────────────────────────────────────────────────────

    def test_helpscout_ticket_basic(self):
        data = {
            "ticket_id": "ticket_001",
            "platform": "helpscout",
            "customer_email": "user@example.com",
            "message": "I need help.",
        }
        result = self.node(data)

        assert result["success"] is True
        ticket = result["ticket"]
        assert ticket["ticket_id"] == "ticket_001"
        assert ticket["platform"].value == "helpscout"
        assert ticket["customer_email"] == "user@example.com"
        assert ticket["message"] == "I need help."

    def test_facebook_platform_mapped(self):
        data = {"platform": "facebook", "message": "Hello"}
        result = self.node(data)
        assert result["success"] is True
        assert result["ticket"]["platform"].value == "facebook"

    def test_platform_field_in_result(self):
        data = {"platform": "helpscout", "message": "test"}
        result = self.node(data)
        assert result["platform"] == "helpscout"

    def test_created_at_parsed_from_iso_string(self):
        ts = "2025-01-15T10:30:00"
        data = {"platform": "helpscout", "message": "x", "created_at": ts}
        result = self.node(data)
        assert isinstance(result["ticket"]["created_at"], datetime)

    def test_created_at_defaults_to_now_when_missing(self):
        data = {"platform": "helpscout", "message": "x"}
        before = datetime.utcnow()
        result = self.node(data)
        after = datetime.utcnow()
        created = result["ticket"]["created_at"]
        assert before <= created <= after

    def test_fallback_ticket_id_generated_when_missing(self):
        data = {"platform": "helpscout", "message": "x"}
        result = self.node(data)
        assert result["success"] is True
        assert result["ticket"]["ticket_id"].startswith("ticket_")

    def test_conversation_id_used_as_ticket_id_fallback(self):
        data = {"platform": "helpscout", "message": "x", "conversation_id": "conv_42"}
        result = self.node(data)
        assert result["ticket"]["ticket_id"] == "conv_42"

    def test_explicit_ticket_id_takes_priority(self):
        data = {
            "platform": "helpscout",
            "message": "x",
            "ticket_id": "T999",
            "conversation_id": "conv_42",
        }
        result = self.node(data)
        assert result["ticket"]["ticket_id"] == "T999"

    def test_customer_email_from_nested_customer_dict(self):
        data = {
            "platform": "helpscout",
            "message": "x",
            "customer": {"email": "nested@example.com", "name": "Ali"},
        }
        result = self.node(data)
        assert result["ticket"]["customer_email"] == "nested@example.com"
        assert result["ticket"]["customer_name"] == "Ali"

    def test_top_level_customer_email_takes_priority(self):
        data = {
            "platform": "helpscout",
            "message": "x",
            "customer_email": "top@example.com",
            "customer": {"email": "nested@example.com"},
        }
        result = self.node(data)
        assert result["ticket"]["customer_email"] == "top@example.com"

    def test_body_used_when_message_missing(self):
        data = {"platform": "helpscout", "body": "body text"}
        result = self.node(data)
        assert result["ticket"]["message"] == "body text"

    def test_is_html_defaults_to_false(self):
        data = {"platform": "helpscout", "message": "x"}
        result = self.node(data)
        assert result["ticket"]["is_html"] is False

    def test_is_html_can_be_true(self):
        data = {"platform": "helpscout", "message": "x", "is_html": True}
        result = self.node(data)
        assert result["ticket"]["is_html"] is True

    # ── Edge cases ──────────────────────────────────────────────────────────

    def test_unknown_platform_defaults_to_helpscout(self):
        data = {"platform": "unknown_xyz", "message": "x"}
        result = self.node(data)
        assert result["success"] is True
        assert result["ticket"]["platform"].value == "helpscout"

    def test_invalid_created_at_falls_back_to_now(self):
        data = {"platform": "helpscout", "message": "x", "created_at": "not-a-date"}
        before = datetime.utcnow()
        result = self.node(data)
        after = datetime.utcnow()
        created = result["ticket"]["created_at"]
        assert before <= created <= after

    def test_empty_payload_returns_success(self):
        result = self.node({})
        assert result["success"] is True
        assert result["ticket"] is not None

    def test_node_does_not_mutate_input(self):
        data = {"platform": "helpscout", "message": "original", "ticket_id": "T1"}
        original_message = data["message"]
        self.node(data)
        assert data["message"] == original_message
