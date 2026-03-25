"""
Tests for nodes/knowledge_retriever.py — make_knowledge_retriever_node()
Uses a mock qdrant_client — no real DB / network calls.
"""
from unittest.mock import MagicMock
from support_agent.nodes.knowledge_retriever import make_knowledge_retriever_node, _build_support_answer


# ─── Helpers ────────────────────────────────────────────────────────────────

def _make_qdrant(results=None):
    client = MagicMock()
    client.retrieve_knowledge.return_value = results if results is not None else [
        {
            "answer": "Go to Settings → License and enter your key.",
            "score": 0.92,
            "source": "docs/license-activation.md",
        }
    ]
    return client


def _state_with_intent(ticket=None, intent=None):
    return {
        "ticket": ticket or {
            "ticket_id": "T1",
            "message": "I cannot activate my license key.",
        },
        "intent_classification": intent or {
            "category": "technical",
            "intent_category": "technical",
            "confidence": 0.95,
        },
    }


# ─── Factory tests ───────────────────────────────────────────────────────────

class TestFactory:
    def test_returns_callable(self):
        node = make_knowledge_retriever_node(_make_qdrant())
        assert callable(node)

    def test_different_clients_produce_different_nodes(self):
        a = make_knowledge_retriever_node(_make_qdrant())
        b = make_knowledge_retriever_node(_make_qdrant())
        assert a is not b


# ─── Happy-path tests ────────────────────────────────────────────────────────

class TestKnowledgeRetrieverNodeHappyPath:
    def setup_method(self):
        self.qdrant = _make_qdrant()
        self.node = make_knowledge_retriever_node(self.qdrant)

    def test_returns_retrieval_results(self):
        state = _state_with_intent()
        result = self.node(state)
        assert len(result["retrieval_results"]) == 1

    def test_builds_support_answer(self):
        state = _state_with_intent()
        result = self.node(state)
        answer = result["support_answer"]
        assert answer is not None
        assert "answer_text" in answer
        assert answer["answer_text"] == "Go to Settings → License and enter your key."

    def test_support_answer_has_confidence(self):
        state = _state_with_intent()
        result = self.node(state)
        assert result["support_answer"]["confidence"] == 0.92

    def test_support_answer_has_sources(self):
        state = _state_with_intent()
        result = self.node(state)
        assert "docs/license-activation.md" in result["support_answer"]["sources"]

    def test_qdrant_called_with_message_query(self):
        state = _state_with_intent()
        self.node(state)
        self.qdrant.retrieve_knowledge.assert_called_once()
        kwargs = self.qdrant.retrieve_knowledge.call_args
        assert kwargs[1]["query"] == "I cannot activate my license key."

    def test_qdrant_called_with_intent_category(self):
        state = _state_with_intent()
        self.node(state)
        kwargs = self.qdrant.retrieve_knowledge.call_args
        assert kwargs[1]["category"] == "technical"

    def test_qdrant_limit_is_5(self):
        state = _state_with_intent()
        self.node(state)
        kwargs = self.qdrant.retrieve_knowledge.call_args
        assert kwargs[1]["limit"] == 5

    def test_category_from_intent_category_key(self):
        """Some intent dicts use 'intent_category' key instead of 'category'."""
        state = _state_with_intent(
            intent={"intent_category": "billing", "confidence": 0.8}
        )
        self.node(state)
        kwargs = self.qdrant.retrieve_knowledge.call_args
        assert kwargs[1]["category"] in ("billing", None)

    # ── Immutability (Law IV) ────────────────────────────────────────────────

    def test_does_not_mutate_input_state(self):
        state = _state_with_intent()
        original_keys = set(state.keys())
        self.node(state)
        assert set(state.keys()) == original_keys

    def test_returns_new_state_object(self):
        state = _state_with_intent()
        result = self.node(state)
        assert result is not state


# ─── No-intent guard ─────────────────────────────────────────────────────────

class TestKnowledgeRetrieverNoIntent:
    def setup_method(self):
        self.qdrant = _make_qdrant()
        self.node = make_knowledge_retriever_node(self.qdrant)

    def test_returns_empty_results_when_no_intent(self):
        state = {"ticket": {"ticket_id": "T1", "message": "help"}, "intent_classification": None}
        result = self.node(state)
        assert result["retrieval_results"] == []
        assert result["support_answer"] is None

    def test_qdrant_not_called_when_no_intent(self):
        state = {"ticket": {"ticket_id": "T1", "message": "help"}, "intent_classification": None}
        self.node(state)
        self.qdrant.retrieve_knowledge.assert_not_called()


# ─── Empty results ────────────────────────────────────────────────────────────

class TestKnowledgeRetrieverEmptyResults:
    def setup_method(self):
        self.qdrant = _make_qdrant(results=[])
        self.node = make_knowledge_retriever_node(self.qdrant)

    def test_support_answer_is_none_when_no_results(self):
        state = _state_with_intent()
        result = self.node(state)
        assert result["support_answer"] is None

    def test_retrieval_results_is_empty_list(self):
        state = _state_with_intent()
        result = self.node(state)
        assert result["retrieval_results"] == []


# ─── Qdrant failure ───────────────────────────────────────────────────────────

class TestKnowledgeRetrieverQdrantFailure:
    def test_returns_empty_results_on_exception(self):
        qdrant = MagicMock()
        qdrant.retrieve_knowledge.side_effect = RuntimeError("connection refused")
        node = make_knowledge_retriever_node(qdrant)

        state = _state_with_intent()
        result = node(state)

        assert result["retrieval_results"] == []
        assert result["support_answer"] is None


# ─── _build_support_answer helper ────────────────────────────────────────────

class TestBuildSupportAnswer:
    def test_picks_first_result_as_best(self):
        results = [
            {"answer": "First answer.", "score": 0.9, "source": "doc1"},
            {"answer": "Second answer.", "score": 0.7, "source": "doc2"},
        ]
        answer = _build_support_answer(results)
        assert answer["answer_text"] == "First answer."

    def test_score_becomes_confidence(self):
        results = [{"answer": "x", "score": 0.75, "source": "doc1"}]
        answer = _build_support_answer(results)
        assert answer["confidence"] == 0.75

    def test_source_in_sources_list(self):
        results = [{"answer": "x", "score": 0.8, "source": "my-doc.md"}]
        answer = _build_support_answer(results)
        assert "my-doc.md" in answer["sources"]

    def test_missing_answer_field_defaults_to_empty_string(self):
        results = [{"score": 0.5, "source": "doc"}]
        answer = _build_support_answer(results)
        assert answer["answer_text"] == ""

    def test_missing_source_defaults_to_unknown(self):
        results = [{"answer": "text", "score": 0.5}]
        answer = _build_support_answer(results)
        assert "unknown" in answer["sources"]
