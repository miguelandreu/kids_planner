from unittest.mock import MagicMock

import pytest

from kids_planner import email_sender_tool
from kids_planner.email_sender_tool import is_dry_run, send_email

from .conftest import call_tool


@pytest.fixture
def smtp(monkeypatch):
    """Sustituye smtplib.SMTP y SMTP_SSL por mocks y devuelve el servidor falso."""
    server = MagicMock()
    server.__enter__.return_value = server
    server.send_message.return_value = {}
    monkeypatch.setattr(email_sender_tool.smtplib, "SMTP", MagicMock(return_value=server))
    monkeypatch.setattr(email_sender_tool.smtplib, "SMTP_SSL", MagicMock(return_value=server))
    return server


def send(**overrides):
    args = {"subject": "Planes", "body": "Sábado: parque"} | overrides
    return call_tool(send_email, **args)


@pytest.mark.parametrize("value, expected", [("1", True), ("TRUE", True), (" yes ", True), ("on", True),
                                             ("0", False), ("", False), ("no", False)])
def test_is_dry_run(monkeypatch, value, expected):
    monkeypatch.setenv("DRY_RUN", value)
    assert is_dry_run() is expected


def test_sends_one_message_to_all_recipients(smtp):
    result = send(html_body="<p>hola</p>")

    assert "sent to 3 recipient(s)" in result
    smtp.starttls.assert_called_once()
    smtp.login.assert_called_once_with("bot@test.com", "secret")
    msg = smtp.send_message.call_args.args[0]
    assert msg["To"] == "a@test.com, b@test.com, c@test.com"
    assert msg["From"] == "bot@test.com"
    assert msg["Subject"] == "Planes"
    assert msg.get_body(("html",)) is not None


def test_port_465_uses_implicit_tls(monkeypatch, smtp):
    monkeypatch.setenv("SMTP_PORT", "465")
    send()
    email_sender_tool.smtplib.SMTP_SSL.assert_called_once()
    smtp.starttls.assert_not_called()


def test_dry_run_prints_and_does_not_connect(monkeypatch, smtp, capsys):
    monkeypatch.setenv("DRY_RUN", "1")
    for key in ("SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD"):
        monkeypatch.delenv(key)

    result = send()

    assert result.startswith("DRY RUN")
    assert "Sábado: parque" in capsys.readouterr().out
    email_sender_tool.smtplib.SMTP.assert_not_called()


def test_second_call_is_blocked_by_guard(smtp):
    send()
    result = send()

    assert "YA se envió" in result
    smtp.send_message.assert_called_once()


def test_dry_run_also_counts_for_guard(monkeypatch, smtp):
    monkeypatch.setenv("DRY_RUN", "1")
    send()
    assert "YA se envió" in send()


def test_failed_send_can_be_retried(smtp):
    smtp.send_message.side_effect = [OSError("boom"), {}]

    first = send()
    second = send()

    assert "sent to" not in first
    assert "sent to 3 recipient(s)" in second
    assert smtp.send_message.call_count == 2


def test_refused_recipients_is_not_counted_as_sent(smtp):
    smtp.send_message.return_value = {"a@test.com": (550, b"no")}
    send()
    assert email_sender_tool._email_sent is False


@pytest.mark.parametrize("overrides", [{"subject": "  "}, {"body": ""}])
def test_empty_subject_or_body_is_rejected(smtp, overrides):
    send(**overrides)
    smtp.send_message.assert_not_called()
    assert email_sender_tool._email_sent is False


def test_invalid_recipient_is_rejected(monkeypatch, smtp):
    monkeypatch.setenv("EMAIL_RECIPIENTS", "ok@test.com, no-es-un-email")
    send()
    smtp.send_message.assert_not_called()
