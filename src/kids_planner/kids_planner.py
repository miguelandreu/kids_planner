import argparse
import asyncio
import os
import sys

from dotenv import load_dotenv

from agents import Agent, Runner, WebSearchTool

from .prompts import INSTRUCTIONS
from .weather_tool import get_weekend_weather
from .email_sender_tool import email_was_sent, send_email

NO_PLANS_TEXT = "no hay planes disponibles"
MAX_TURNS = 25  # el defecto del SDK es 10; las búsquedas web consumen varios turnos


async def run():

    model = os.getenv("OPENAI_MODEL") or "gpt-6-luna"


    agent = Agent(
        name="Planes con niños",
        instructions=INSTRUCTIONS,
        model=model,
        tools=[get_weekend_weather, WebSearchTool(), send_email],
    )

    result = await Runner.run(
        agent,
        "¿Qué podemos hacer este fin de semana con dos niños de 2 y 5 años?",
        max_turns=MAX_TURNS,
    )

    return str(result.final_output)


def main():
    parser = argparse.ArgumentParser(description="Planes con niños para el fin de semana")
    parser.add_argument("--dry-run", action="store_true",
                        help="imprime el email en vez de enviarlo (equivale a DRY_RUN=1)")
    args = parser.parse_args()

    load_dotenv()
    if args.dry_run:
        os.environ["DRY_RUN"] = "1"
    output = asyncio.run(run())
    print(output)

    # Salida != 0 si no se envió el correo, salvo que el agente indique que no hay planes
    # (en ese caso el prompt le ordena no enviar nada y no es un fallo).
    if email_was_sent():
        return
    if NO_PLANS_TEXT in output.lower():
        print("Sin planes disponibles: no se envió correo.")
        return
    print("ERROR: el correo no se envió y el agente no indicó que no hubiera planes.", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()