import asyncio
import json

import pytest
from agents.tool_context import ToolContext

from kids_planner import email_sender_tool

SMTP_ENV = {
    "SMTP_HOST": "smtp.test",
    "SMTP_PORT": "587",
    "SMTP_USERNAME": "bot@test.com",
    "SMTP_PASSWORD": "secret",
    "EMAIL_RECIPIENTS": "a@test.com; b@test.com,c@test.com",
}


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch):
    """Entorno hermético: sin .env real, sin DRY_RUN y con el guard de email reiniciado."""
    monkeypatch.setattr(email_sender_tool, "load_dotenv", lambda: None)
    monkeypatch.setattr(email_sender_tool, "_email_sent", False)
    monkeypatch.delenv("DRY_RUN", raising=False)
    monkeypatch.delenv("EMAIL_FROM", raising=False)
    for key, value in SMTP_ENV.items():
        monkeypatch.setenv(key, value)


def call_tool(tool, **arguments):
    """Invoca una function_tool del Agents SDK igual que lo haría el agente."""
    ctx = ToolContext(context=None, tool_name=tool.name, tool_call_id="test", tool_arguments="{}")
    return asyncio.run(tool.on_invoke_tool(ctx, json.dumps(arguments)))
