from datetime import timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


def test_generate_content_returns_content_piece_list(
    sample_content_request,
    sample_content_plan,
    sample_fact_sheet,
) -> None:
    from services.claude_client import ClaudeContentClient

    response = SimpleNamespace(
        content=[
            SimpleNamespace(
                text='{"variants":[{"label":"A","body":"نسخة أ"},{"label":"B","body":"نسخة ب"}]}'
            )
        ]
    )
    fake_client = MagicMock()
    fake_client.messages.create.return_value = response

    with patch("services.claude_client.anthropic.Anthropic", return_value=fake_client):
        client = ClaudeContentClient(api_key="test-key")
        pieces = client.generate_content(
            sample_content_request,
            sample_content_plan,
            sample_fact_sheet,
        )

    assert len(pieces) == 2
    assert pieces[0].variant_label == "A"
    assert pieces[1].variant_label == "B"


def test_generate_content_uses_timezone_aware_created_at(
    sample_content_request,
    sample_content_plan,
    sample_fact_sheet,
) -> None:
    from services.claude_client import ClaudeContentClient

    response = SimpleNamespace(
        content=[SimpleNamespace(text='{"variants":[{"label":"A","body":"نسخة"}]}')]
    )
    fake_client = MagicMock()
    fake_client.messages.create.return_value = response

    with patch("services.claude_client.anthropic.Anthropic", return_value=fake_client):
        client = ClaudeContentClient(api_key="test-key")
        pieces = client.generate_content(
            sample_content_request,
            sample_content_plan,
            sample_fact_sheet,
        )

    assert pieces[0].created_at.tzinfo == timezone.utc


def test_generate_content_handles_json_parse_error_without_crash(
    sample_content_request,
    sample_content_plan,
    sample_fact_sheet,
) -> None:
    from services.claude_client import ClaudeContentClient

    response = SimpleNamespace(content=[SimpleNamespace(text="{not-json")])
    fake_client = MagicMock()
    fake_client.messages.create.return_value = response

    with patch("services.claude_client.anthropic.Anthropic", return_value=fake_client):
        client = ClaudeContentClient(api_key="test-key")
        pieces = client.generate_content(
            sample_content_request,
            sample_content_plan,
            sample_fact_sheet,
        )

    assert len(pieces) == 2
    assert all(piece.created_at.tzinfo == timezone.utc for piece in pieces)
