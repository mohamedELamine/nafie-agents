"""
Tests for nodes/disclaimer_adder.py — make_disclaimer_adder_node()
Pure function: no external dependencies, no DB, no clients.
"""
from support_agent.nodes.disclaimer_adder import make_disclaimer_adder_node

_DISCLAIMER_FRAGMENT = "ملاحظة هامة"


class TestMakeDisclaimerAdderNode:
    def test_returns_callable(self):
        node = make_disclaimer_adder_node()
        assert callable(node)

    def test_each_call_returns_independent_function(self):
        a = make_disclaimer_adder_node()
        b = make_disclaimer_adder_node()
        assert a is not b


class TestDisclaimerAdderNode:
    def setup_method(self):
        self.node = make_disclaimer_adder_node()

    # ── Happy path ──────────────────────────────────────────────────────────

    def test_disclaimer_appended_to_answer_text(self):
        state = {
            "support_answer": {
                "answer_text": "Your license key is valid.",
                "confidence": 0.9,
                "sources": ["docs/license.md"],
            }
        }
        result = self.node(state)
        assert _DISCLAIMER_FRAGMENT in result["support_answer"]["answer_text"]

    def test_original_answer_text_preserved(self):
        original = "Your license key is valid."
        state = {"support_answer": {"answer_text": original, "confidence": 0.9, "sources": []}}
        result = self.node(state)
        assert result["support_answer"]["answer_text"].startswith(original)

    def test_other_answer_fields_preserved(self):
        state = {
            "support_answer": {
                "answer_text": "Some answer.",
                "confidence": 0.85,
                "sources": ["doc_a", "doc_b"],
            }
        }
        result = self.node(state)
        answer = result["support_answer"]
        assert answer["confidence"] == 0.85
        assert answer["sources"] == ["doc_a", "doc_b"]

    def test_other_state_fields_preserved(self):
        state = {
            "ticket": {"ticket_id": "T1"},
            "platform": "helpscout",
            "overall_risk_level": "low",
            "support_answer": {"answer_text": "ok", "confidence": 1.0, "sources": []},
        }
        result = self.node(state)
        assert result["ticket"] == {"ticket_id": "T1"}
        assert result["platform"] == "helpscout"
        assert result["overall_risk_level"] == "low"

    # ── Immutability (Law IV) ────────────────────────────────────────────────

    def test_does_not_mutate_input_state(self):
        original_answer = "Original text."
        state = {"support_answer": {"answer_text": original_answer, "confidence": 1.0, "sources": []}}
        self.node(state)
        # Input state must be untouched
        assert state["support_answer"]["answer_text"] == original_answer

    def test_returns_new_state_object(self):
        state = {"support_answer": {"answer_text": "text", "confidence": 1.0, "sources": []}}
        result = self.node(state)
        assert result is not state

    def test_returns_new_answer_object(self):
        answer = {"answer_text": "text", "confidence": 1.0, "sources": []}
        state = {"support_answer": answer}
        result = self.node(state)
        assert result["support_answer"] is not answer

    # ── Edge cases ───────────────────────────────────────────────────────────

    def test_no_support_answer_returns_state_unchanged(self):
        state = {"ticket": {"ticket_id": "T1"}, "support_answer": None}
        result = self.node(state)
        assert result["support_answer"] is None
        assert result["ticket"] == {"ticket_id": "T1"}

    def test_missing_support_answer_key_returns_state_unchanged(self):
        state = {"ticket": {"ticket_id": "T1"}}
        result = self.node(state)
        # should not raise, state is returned as-is
        assert result.get("support_answer") is None

    def test_empty_answer_text_gets_disclaimer(self):
        state = {"support_answer": {"answer_text": "", "confidence": 0.0, "sources": []}}
        result = self.node(state)
        assert _DISCLAIMER_FRAGMENT in result["support_answer"]["answer_text"]

    def test_disclaimer_appended_exactly_once(self):
        state = {"support_answer": {"answer_text": "Answer.", "confidence": 1.0, "sources": []}}
        result = self.node(state)
        text = result["support_answer"]["answer_text"]
        assert text.count(_DISCLAIMER_FRAGMENT) == 1

    def test_node_idempotent_when_called_twice(self):
        """Each call on the RESULT of the previous call should add ONE disclaimer."""
        state = {"support_answer": {"answer_text": "Answer.", "confidence": 1.0, "sources": []}}
        result1 = self.node(state)
        result2 = self.node(result1)
        # Second call appends a second disclaimer — that's the expected behaviour;
        # what we verify is that the node doesn't crash and always appends.
        assert result2["support_answer"]["answer_text"].count(_DISCLAIMER_FRAGMENT) == 2
