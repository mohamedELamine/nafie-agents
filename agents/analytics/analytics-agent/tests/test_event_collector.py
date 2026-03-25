"""
Tests for workflows/event_collector.py — event_collector_node()
All DB interactions are mocked via patch on get_conn and db functions.
"""
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _make_event(**overrides):
    base = {
        "event_id": "evt_001",
        "event_type": "NEW_SALE",
        "source": "lemon_squeezy",
        "occurred_at": "2025-06-15T14:30:00",
        "data": {
            "theme_slug": "my-theme",
            "amount_usd": 39.0,
            "order_id": "ORD-001",
        },
    }
    base.update(overrides)
    return base


# ─── event_collector_node ────────────────────────────────────────────────────

class TestEventCollectorNode:

    def _run(self, event, conn_mock, event_exists_return=False, attribution_side_effect=None):
        """Helper: run event_collector_node with mocked DB."""
        from contextlib import contextmanager

        @contextmanager
        def fake_get_conn():
            yield conn_mock

        with patch("analytics_agent.workflows.event_collector.get_conn", fake_get_conn), \
             patch("analytics_agent.workflows.event_collector.event_store.event_exists",
                   return_value=event_exists_return) as mock_exists, \
             patch("analytics_agent.workflows.event_collector.event_store.save_event") as mock_save, \
             patch("analytics_agent.workflows.event_collector.attribute_sale") as mock_attr:

            if attribution_side_effect:
                mock_attr.side_effect = attribution_side_effect

            from analytics_agent.workflows.event_collector import event_collector_node
            event_collector_node(event)

            return mock_exists, mock_save, mock_attr

    def test_saves_new_event_to_db(self):
        conn = MagicMock()
        event = _make_event()
        _, mock_save, _ = self._run(event, conn)
        mock_save.assert_called_once()

    def test_skips_duplicate_event(self):
        conn = MagicMock()
        event = _make_event()
        _, mock_save, _ = self._run(event, conn, event_exists_return=True)
        mock_save.assert_not_called()

    def test_event_exists_checked_first(self):
        conn = MagicMock()
        event = _make_event()
        mock_exists, _, _ = self._run(event, conn)
        mock_exists.assert_called_once_with(conn, "evt_001")

    def test_event_without_event_id_skipped(self):
        conn = MagicMock()
        event = {"event_type": "NEW_SALE", "source": "lemon_squeezy"}  # no event_id
        from contextlib import contextmanager

        @contextmanager
        def fake_get_conn():
            yield conn

        with patch("analytics_agent.workflows.event_collector.get_conn", fake_get_conn), \
             patch("analytics_agent.workflows.event_collector.event_store.event_exists") as mock_exists, \
             patch("analytics_agent.workflows.event_collector.event_store.save_event") as mock_save:

            from analytics_agent.workflows.event_collector import event_collector_node
            event_collector_node(event)

            mock_exists.assert_not_called()
            mock_save.assert_not_called()

    def test_occurred_at_parsed_from_iso_string(self):
        conn = MagicMock()
        event = _make_event(occurred_at="2025-01-15T10:30:00")
        saved_event = {}

        def capture_save(c, e):
            saved_event.update(e)

        from contextlib import contextmanager

        @contextmanager
        def fake_get_conn():
            yield conn

        with patch("analytics_agent.workflows.event_collector.get_conn", fake_get_conn), \
             patch("analytics_agent.workflows.event_collector.event_store.event_exists", return_value=False), \
             patch("analytics_agent.workflows.event_collector.event_store.save_event", side_effect=capture_save), \
             patch("analytics_agent.workflows.event_collector.attribute_sale"):

            from analytics_agent.workflows.event_collector import event_collector_node
            event_collector_node(event)

        assert isinstance(saved_event.get("occurred_at"), datetime)

    def test_occurred_at_falls_back_to_now_when_missing(self):
        conn = MagicMock()
        event = _make_event()
        del event["occurred_at"]
        saved_event = {}

        def capture_save(c, e):
            saved_event.update(e)

        from contextlib import contextmanager

        @contextmanager
        def fake_get_conn():
            yield conn

        before = datetime.now(timezone.utc)
        with patch("analytics_agent.workflows.event_collector.get_conn", fake_get_conn), \
             patch("analytics_agent.workflows.event_collector.event_store.event_exists", return_value=False), \
             patch("analytics_agent.workflows.event_collector.event_store.save_event", side_effect=capture_save), \
             patch("analytics_agent.workflows.event_collector.attribute_sale"):

            from analytics_agent.workflows.event_collector import event_collector_node
            event_collector_node(event)

        after = datetime.now(timezone.utc)
        occurred = saved_event.get("occurred_at")
        assert occurred is not None
        assert before <= occurred <= after

    def test_attribution_called_for_new_sale(self):
        conn = MagicMock()
        event = _make_event(event_type="NEW_SALE")
        _, _, mock_attr = self._run(event, conn)
        mock_attr.assert_called_once()

    def test_attribution_not_called_for_non_sale_event(self):
        conn = MagicMock()
        event = _make_event(event_type="SUPPORT_TICKET_OPENED")
        _, _, mock_attr = self._run(event, conn)
        mock_attr.assert_not_called()

    def test_attribution_failure_does_not_crash_node(self):
        conn = MagicMock()
        event = _make_event(event_type="NEW_SALE")
        # Should not raise
        self._run(event, conn, attribution_side_effect=RuntimeError("attribution failed"))

    def test_theme_slug_extracted_from_data(self):
        conn = MagicMock()
        event = _make_event(data={"theme_slug": "my-special-theme"})
        saved_event = {}

        def capture_save(c, e):
            saved_event.update(e)

        from contextlib import contextmanager

        @contextmanager
        def fake_get_conn():
            yield conn

        with patch("analytics_agent.workflows.event_collector.get_conn", fake_get_conn), \
             patch("analytics_agent.workflows.event_collector.event_store.event_exists", return_value=False), \
             patch("analytics_agent.workflows.event_collector.event_store.save_event", side_effect=capture_save), \
             patch("analytics_agent.workflows.event_collector.attribute_sale"):

            from analytics_agent.workflows.event_collector import event_collector_node
            event_collector_node(event)

        assert saved_event.get("theme_slug") == "my-special-theme"

    def test_save_event_includes_event_id(self):
        conn = MagicMock()
        event = _make_event(event_id="evt_unique_999")
        saved_event = {}

        def capture_save(c, e):
            saved_event.update(e)

        from contextlib import contextmanager

        @contextmanager
        def fake_get_conn():
            yield conn

        with patch("analytics_agent.workflows.event_collector.get_conn", fake_get_conn), \
             patch("analytics_agent.workflows.event_collector.event_store.event_exists", return_value=False), \
             patch("analytics_agent.workflows.event_collector.event_store.save_event", side_effect=capture_save), \
             patch("analytics_agent.workflows.event_collector.attribute_sale"):

            from analytics_agent.workflows.event_collector import event_collector_node
            event_collector_node(event)

        assert saved_event.get("event_id") == "evt_unique_999"


# ─── Constitutional Law I: occurred_at vs received_at ────────────────────────

class TestOccurredAtLaw:
    """
    Constitutional Law I: occurred_at is used for analysis; received_at for diagnostics.
    The event_collector must store occurred_at from the event payload (not fabricate it),
    and must include a separate received_at (the ingestion timestamp).
    """

    def _capture_saved(self, event):
        conn = MagicMock()
        saved = {}

        def capture(c, e):
            saved.update(e)

        from contextlib import contextmanager

        @contextmanager
        def fake_get_conn():
            yield conn

        with patch("analytics_agent.workflows.event_collector.get_conn", fake_get_conn), \
             patch("analytics_agent.workflows.event_collector.event_store.event_exists", return_value=False), \
             patch("analytics_agent.workflows.event_collector.event_store.save_event", side_effect=capture), \
             patch("analytics_agent.workflows.event_collector.attribute_sale"):

            from analytics_agent.workflows.event_collector import event_collector_node
            event_collector_node(event)

        return saved

    def test_occurred_at_preserved_from_event(self):
        event = _make_event(occurred_at="2025-01-01T00:00:00")
        saved = self._capture_saved(event)
        assert saved["occurred_at"] == datetime(2025, 1, 1, 0, 0, 0)

    def test_received_at_is_current_time(self):
        event = _make_event(occurred_at="2020-01-01T00:00:00")
        before = datetime.now(timezone.utc)
        saved = self._capture_saved(event)
        after = datetime.now(timezone.utc)
        assert before <= saved["received_at"] <= after

    def test_received_at_not_used_as_occurred_at(self):
        """When occurred_at is an old date, saved occurred_at must not be 'now'."""
        old_date = "2020-03-10T08:00:00"
        event = _make_event(occurred_at=old_date)
        saved = self._capture_saved(event)
        expected = datetime(2020, 3, 10, 8, 0, 0)
        assert saved["occurred_at"] == expected
        # received_at should be significantly later
        assert saved["received_at"] > expected.replace(tzinfo=timezone.utc)
