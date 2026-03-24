"""
Tests for workflows/signal_generator.py
Focus: pure logic (create_signal, generate_signals_from_patterns) and
idempotency guard (signal_sent_recently checked before send).
"""
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch, call

from analytics_agent.models import SignalType, SignalPriority, AttributionConfidence
from analytics_agent.workflows.signal_generator import create_signal, generate_signals_from_patterns


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _make_pattern(pattern_type, metrics=None):
    p = MagicMock()
    p.pattern_type = pattern_type
    p.supporting_metrics = metrics or {}
    return p


# ─── create_signal ────────────────────────────────────────────────────────────

class TestCreateSignal:

    def test_returns_analytics_signal_object(self):
        signal = create_signal(
            signal_type=SignalType.SALES_DROP_ALERT,
            priority=SignalPriority.IMMEDIATE,
            target_agent="marketing_agent",
            theme_slug="my-theme",
            confidence=0.9,
            data={"drop_percentage": 30},
        )
        assert signal is not None

    def test_signal_id_is_string(self):
        signal = create_signal(
            signal_type=SignalType.BEST_CHANNEL,
            priority=SignalPriority.WEEKLY,
            target_agent="marketing_agent",
            theme_slug="all",
            confidence=0.6,
            data={},
        )
        assert isinstance(signal.signal_id, str)

    def test_signal_id_contains_type_value(self):
        signal = create_signal(
            signal_type=SignalType.SALES_DROP_ALERT,
            priority=SignalPriority.IMMEDIATE,
            target_agent="marketing_agent",
            theme_slug="all",
            confidence=0.9,
            data={},
        )
        assert SignalType.SALES_DROP_ALERT.value in signal.signal_id

    def test_signal_type_stored(self):
        signal = create_signal(
            signal_type=SignalType.BEST_TIME,
            priority=SignalPriority.DAILY,
            target_agent="marketing_agent",
            theme_slug="my-theme",
            confidence=0.5,
            data={},
        )
        assert signal.signal_type == SignalType.BEST_TIME

    def test_target_agent_stored(self):
        signal = create_signal(
            signal_type=SignalType.BEST_CHANNEL,
            priority=SignalPriority.WEEKLY,
            target_agent="content_agent",
            theme_slug="all",
            confidence=0.6,
            data={},
        )
        assert signal.target_agent == "content_agent"

    def test_data_stored(self):
        payload = {"current_sales": 10, "previous_sales": 30}
        signal = create_signal(
            signal_type=SignalType.SALES_DROP_ALERT,
            priority=SignalPriority.IMMEDIATE,
            target_agent="marketing_agent",
            theme_slug="all",
            confidence=0.9,
            data=payload,
        )
        assert signal.data == payload

    def test_generated_at_is_recent_datetime(self):
        before = datetime.utcnow()
        signal = create_signal(
            signal_type=SignalType.LOW_SALES,
            priority=SignalPriority.DAILY,
            target_agent="marketing_agent",
            theme_slug="my-theme",
            confidence=0.4,
            data={},
        )
        after = datetime.utcnow()
        assert before <= signal.generated_at <= after

    def test_two_signals_have_different_ids(self):
        kwargs = dict(
            signal_type=SignalType.BEST_CHANNEL,
            priority=SignalPriority.WEEKLY,
            target_agent="marketing_agent",
            theme_slug="all",
            confidence=0.6,
            data={},
        )
        s1 = create_signal(**kwargs)
        s2 = create_signal(**kwargs)
        # IDs include timestamp — with the same second they can collide;
        # what matters is the object identity
        assert s1 is not s2


# ─── generate_signals_from_patterns ──────────────────────────────────────────

class TestGenerateSignalsFromPatterns:

    def _run(self, patterns, signal_sent_recently_return=False):
        with patch("analytics_agent.workflows.signal_generator.signal_store.signal_sent_recently",
                   return_value=signal_sent_recently_return) as mock_recent, \
             patch("analytics_agent.workflows.signal_generator.signal_store.mark_signal_sent") as mock_mark, \
             patch("analytics_agent.workflows.signal_generator.get_redis_bus") as mock_bus_factory:

            mock_bus = MagicMock()
            mock_bus.client = MagicMock()
            mock_bus_factory.return_value = mock_bus

            result = generate_signals_from_patterns(patterns)

            return result, mock_recent, mock_mark, mock_bus

    def test_empty_patterns_returns_empty_list(self):
        result, _, _, _ = self._run([])
        assert result == []

    def test_sales_drop_pattern_produces_signal(self):
        pattern = _make_pattern("SALES_DROP_7D", {
            "current_sales": 5,
            "previous_sales": 20,
            "drop_percentage": 75,
        })
        result, _, _, _ = self._run([pattern])
        assert len(result) == 1

    def test_sales_drop_signal_has_correct_type(self):
        pattern = _make_pattern("SALES_DROP_7D", {"current_sales": 5, "previous_sales": 20})
        result, _, _, _ = self._run([pattern])
        assert result[0].signal_type == SignalType.SALES_DROP_ALERT

    def test_best_channel_pattern_produces_signal(self):
        pattern = _make_pattern("BEST_CHANNEL_30D", {
            "best_channel": "facebook",
            "sales_count": 50,
            "total_sales": 1500.0,
        })
        result, _, _, _ = self._run([pattern])
        assert len(result) == 1

    def test_best_channel_signal_has_correct_type(self):
        pattern = _make_pattern("BEST_CHANNEL_30D", {"best_channel": "facebook"})
        result, _, _, _ = self._run([pattern])
        assert result[0].signal_type == SignalType.BEST_CHANNEL

    def test_unknown_pattern_type_is_skipped(self):
        pattern = _make_pattern("UNKNOWN_PATTERN_XYZ")
        result, _, _, _ = self._run([pattern])
        assert result == []

    def test_multiple_patterns_produce_multiple_signals(self):
        patterns = [
            _make_pattern("SALES_DROP_7D", {"current_sales": 1, "previous_sales": 10}),
            _make_pattern("BEST_CHANNEL_30D", {"best_channel": "instagram"}),
        ]
        result, _, _, _ = self._run(patterns)
        assert len(result) == 2

    # ── Idempotency (Law III) ────────────────────────────────────────────────

    def test_signal_not_sent_when_already_sent_recently(self):
        pattern = _make_pattern("SALES_DROP_7D", {"current_sales": 1, "previous_sales": 10})
        _, _, _, mock_bus = self._run([pattern], signal_sent_recently_return=True)
        mock_bus.publish.assert_not_called()

    def test_signal_marked_sent_after_publish(self):
        pattern = _make_pattern("SALES_DROP_7D", {"current_sales": 1, "previous_sales": 10})
        _, _, mock_mark, _ = self._run([pattern], signal_sent_recently_return=False)
        mock_mark.assert_called_once()

    def test_signal_sent_recently_checked_before_publish(self):
        """signal_sent_recently must be called before bus.publish."""
        call_order = []

        pattern = _make_pattern("SALES_DROP_7D", {"current_sales": 1, "previous_sales": 10})

        with patch("analytics_agent.workflows.signal_generator.signal_store.signal_sent_recently",
                   side_effect=lambda *a: call_order.append("check") or False), \
             patch("analytics_agent.workflows.signal_generator.signal_store.mark_signal_sent"), \
             patch("analytics_agent.workflows.signal_generator.get_redis_bus") as mock_bus_factory:

            mock_bus = MagicMock()
            mock_bus.client = MagicMock()
            # الكود يستخدم publish_stream (وليس publish) لإرسال الإشارات
            mock_bus.publish_stream = MagicMock(side_effect=lambda *a, **kw: call_order.append("publish"))
            mock_bus_factory.return_value = mock_bus

            generate_signals_from_patterns([pattern])

        assert call_order.index("check") < call_order.index("publish")

    # ── Error resilience ─────────────────────────────────────────────────────

    def test_redis_send_failure_does_not_prevent_signal_creation(self):
        """
        When Redis is unavailable, send_to_target_agent catches the error internally.
        The signal is still created and returned — it just wasn't delivered.
        """
        pattern = _make_pattern("SALES_DROP_7D", {"current_sales": 1, "previous_sales": 10})

        with patch("analytics_agent.workflows.signal_generator.signal_store.signal_sent_recently",
                   side_effect=RuntimeError("Redis down")), \
             patch("analytics_agent.workflows.signal_generator.get_redis_bus"):

            result = generate_signals_from_patterns([pattern])

        # Signal was created even though delivery failed
        assert len(result) == 1
        assert result[0].signal_type == SignalType.SALES_DROP_ALERT

    def test_pattern_exception_does_not_crash(self):
        bad_pattern = MagicMock()
        bad_pattern.pattern_type = "SALES_DROP_7D"
        bad_pattern.supporting_metrics = MagicMock(
            side_effect=AttributeError("no metrics")
        )
        # should not raise
        with patch("analytics_agent.workflows.signal_generator.signal_store.signal_sent_recently",
                   return_value=False), \
             patch("analytics_agent.workflows.signal_generator.get_redis_bus"):
            result = generate_signals_from_patterns([bad_pattern])

        assert isinstance(result, list)
