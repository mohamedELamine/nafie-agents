import asyncio
from datetime import timezone
from types import SimpleNamespace


def test_batch_recorder_saves_batch_to_db(
    visual_env: SimpleNamespace,
    mock_get_conn,
    sample_batch_state,
) -> None:
    module = visual_env.load_module(
        "visual_production_agent.nodes.batch_recorder",
        visual_env.agent_dir / "nodes" / "batch_recorder.py",
    )
    module.get_conn = mock_get_conn

    result = asyncio.run(
        module.BatchRecorderNode()(
            batch_id=sample_batch_state["batch_id"],
            theme_slug=sample_batch_state["theme_slug"],
            version=sample_batch_state["version"],
            total_cost=0.32,
            assets=sample_batch_state["assets"],
            status="published",
        )
    )

    assert result["batch_id"] == "batch_123"
    assert mock_get_conn.calls == 1
    visual_env.db.save_batch.assert_called_once()
    visual_env.db.save_manifest.assert_called_once()


def test_batch_recorder_uses_timezone_aware_started_at(
    visual_env: SimpleNamespace,
    mock_get_conn,
    sample_batch_state,
) -> None:
    module = visual_env.load_module(
        "visual_production_agent.nodes.batch_recorder",
        visual_env.agent_dir / "nodes" / "batch_recorder.py",
    )
    module.get_conn = mock_get_conn

    asyncio.run(
        module.BatchRecorderNode()(
            batch_id=sample_batch_state["batch_id"],
            theme_slug=sample_batch_state["theme_slug"],
            version=sample_batch_state["version"],
            total_cost=0.32,
            assets=sample_batch_state["assets"],
            status="published",
        )
    )

    saved_batch = visual_env.db.save_batch.call_args.args[1]
    assert saved_batch["started_at"].tzinfo == timezone.utc
