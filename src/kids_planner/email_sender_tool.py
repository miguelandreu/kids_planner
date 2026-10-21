"""Email tool: send the generated menu + grocery list to the fixed recipients over SMTP.

Plain function with type hints + docstring, so the OpenAI Agents SDK can turn it into
a tool directly:  `from agents import function_tool; tool = function_tool(send_menu_email)`

The recipients are NOT a tool argument: they come from EMAIL_RECIPIENTS, so the model
cannot send mail anywhere else.

Env vars: SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD, EMAIL_RECIPIENTS (comma or semicolon separated),
SMTP_PORT (default 587; 465 = implicit TLS, anything else = STARTTLS), EMAIL_FROM (default SMTP_USERNAME).
"""
from __future__ import annotations

import os
import re
import smtplib
import ssl
from email.message import EmailMessage

from agents import function_tool

from dotenv import load_dotenv

_TIMEOUT_SECONDS = 30

# Guard anti-duplicados: solo se envía un correo por ejecución.
_email_sent = False


def email_was_sent() -> bool:
    """True si send_email terminó correctamente en esta ejecución."""
    return _email_sent


def is_dry_run() -> bool:
    """True si DRY_RUN está activo (1/true/yes/on): el email se imprime en vez de enviarse."""
    return os.getenv("DRY_RUN", "").strip().lower() in {"1", "true", "yes", "on"}


@function_tool
def send_email(subject: str, body: str, html_body: str | None = None) -> str:
    """Envía por correo electrónico el plan final para el fin de semana a la lista
    de destinatarios ya configurada. Los destinatarios NO se pasan como parámetro:
    son fijos y los gestiona el sistema.

    Úsala una sola vez, al final, cuando ya tengas la previsión del tiempo y los
    planes elegidos. No la uses para borradores, preguntas al usuario ni mensajes
    intermedios, porque el envío es inmediato e irreversible. Si falla, no la
    reintentes más de una vez: informa del error en tu respuesta final.

    Args:
        subject: Asunto del correo, breve y concreto (máx. ~80 caracteres), por
            ejemplo "Planes con niños en Alcobendas: sábado 24 y domingo 25 de
            octubre". No puede estar vacío.
        body: Contenido en texto plano. Es obligatorio y se muestra siempre,
            incluso en clientes que no renderizan HTML. Estructúralo por día
            (sábado, domingo) y por franja (mañana, tarde). Para cada plan
            incluye: nombre, lugar o municipio, si es de interior o exterior,
            por qué encaja con el tiempo previsto y, si lo tienes, el enlace.
            Empieza con una línea resumen del tiempo del fin de semana. No
            puede estar vacío.
        html_body: Versión HTML opcional del mismo contenido, con títulos por
            día y enlaces clicables. Debe contener exactamente la misma
            información que `body`, solo con mejor formato. Omítelo si no estás
            seguro de generar HTML válido.

    Returns:
        Un mensaje de confirmación con el asunto y el número de destinatarios.
        Si lanza una excepción, el correo NO se ha enviado.
    """
    global _email_sent
    if _email_sent:
        return "El correo YA se envió en esta ejecución. No se envía de nuevo; no vuelvas a llamar a esta herramienta."

    load_dotenv()
    dry_run = is_dry_run()
    sender = os.getenv("EMAIL_FROM") or os.getenv("SMTP_USERNAME") or "dry-run@localhost"

    recipients_raw = os.getenv("EMAIL_RECIPIENTS", "") if dry_run else os.environ["EMAIL_RECIPIENTS"]
    recipients = [r.strip() for r in re.split(r"[,;\n]", recipients_raw) if r.strip()]
    if not recipients:
        raise ValueError("EMAIL_RECIPIENTS is empty.")
    bad = [r for r in recipients if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", r)]
    if bad:
        raise ValueError(f"EMAIL_RECIPIENTS contains invalid address(es): {bad}")
    if not subject.strip() or not body.strip():
        raise ValueError("Refusing to send an email with an empty subject or body.")

    msg = EmailMessage()
    msg["Subject"] = subject.strip()
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg.set_content(body)
    if html_body:
        msg.add_alternative(html_body, subtype="html")

    if dry_run:
        print("=== DRY RUN: email NOT sent ===")
        print(f"From: {sender}\nTo: {msg['To']}\nSubject: {msg['Subject']}\n")
        print(body)
        if html_body:
            print("\n--- HTML body ---")
            print(html_body)
        print("=== END DRY RUN ===")
        _email_sent = True
        return f"DRY RUN: email '{msg['Subject']}' not sent ({len(recipients)} recipient(s))."

    host = os.environ["SMTP_HOST"]
    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.environ["SMTP_USERNAME"]
    password = os.environ["SMTP_PASSWORD"]

    context = ssl.create_default_context()
    if port == 465:
        server = smtplib.SMTP_SSL(host, port, timeout=_TIMEOUT_SECONDS, context=context)
    else:
        server = smtplib.SMTP(host, port, timeout=_TIMEOUT_SECONDS)
    with server:
        if port != 465:
            server.starttls(context=context)
        server.login(username, password)
        refused = server.send_message(msg)

    if refused:
        raise RuntimeError(f"SMTP server refused some recipients: {sorted(refused)}")
    _email_sent = True
    return f"Email '{msg['Subject']}' sent to {len(recipients)} recipient(s)."
