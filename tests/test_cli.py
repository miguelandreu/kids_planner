import os
import sys

import pytest

from kids_planner import kids_planner


def run_main(monkeypatch, argv=(), output="resultado", email_sent=True):
    async def fake_run():
        return output

    monkeypatch.setattr(sys, "argv", ["kids-planner", *argv])
    monkeypatch.setattr(kids_planner, "run", fake_run)
    monkeypatch.setattr(kids_planner, "load_dotenv", lambda: None)
    monkeypatch.setattr(kids_planner, "email_was_sent", lambda: email_sent)
    monkeypatch.setenv("DRY_RUN", "")
    kids_planner.main()


def test_dry_run_flag_sets_env(monkeypatch, capsys):
    run_main(monkeypatch, ["--dry-run"])
    assert os.environ["DRY_RUN"] == "1"
    assert "resultado" in capsys.readouterr().out


def test_without_flag_does_not_enable_dry_run(monkeypatch):
    run_main(monkeypatch)
    assert os.environ["DRY_RUN"] == ""


def test_exit_ok_when_email_sent(monkeypatch):
    run_main(monkeypatch, email_sent=True)  # no lanza SystemExit


def test_exit_ok_when_agent_reports_no_plans(monkeypatch, capsys):
    run_main(monkeypatch, output="Lo siento, No hay planes disponibles este fin de semana.", email_sent=False)
    assert "no se envió correo" in capsys.readouterr().out


def test_exit_error_when_email_not_sent_and_plans_exist(monkeypatch, capsys):
    with pytest.raises(SystemExit) as exc:
        run_main(monkeypatch, output="Aquí tienes los planes...", email_sent=False)
    assert exc.value.code == 1
    assert "no se envió" in capsys.readouterr().err
