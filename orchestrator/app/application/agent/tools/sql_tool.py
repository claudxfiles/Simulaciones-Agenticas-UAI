"""Tool: consultar_ventas_mad_market — delega en el sub-agente text-to-SQL.

Adaptado de madxerax-agents/agent-sql/agent.py: mismo loop de tool-calling
MCP contra servidor_mcp.py (SQLite de solo lectura), sin la capa CLI/argparse
del script original. Se expone como una única tool LangChain que el grafo
del orquestador invoca como una caja negra — el sub-agente hace su propio
razonamiento multi-paso (schema → SQL → resultado) con OpenAI directo.
"""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from langchain_core.tools import tool
from openai import AsyncOpenAI

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from app.config import get_settings

logger = logging.getLogger(__name__)

_MCP_DIR = Path(__file__).parent.parent.parent.parent / "infrastructure" / "mcp"
_SERVIDOR = _MCP_DIR / "servidor_mcp.py"

_MODELO = "gpt-4o-mini"
_MAX_PASOS = 6

_PROMPT_SISTEMA = """Eres un analista de datos que responde preguntas sobre la base de datos
de mad_market (retail) consultando SQLite a través de las herramientas MCP disponibles.

Procedimiento obligatorio:
1. Si aún no conoces el esquema, llama primero a `esquema_completo`. No adivines nombres
   de tablas ni de columnas.
2. Escribe UNA consulta SELECT que responda la pregunta y ejecútala con `ejecutar_consulta`.
3. Si la consulta devuelve un error o no devuelve filas, corrígela y vuelve a intentar.
4. Con los resultados en mano, responde en lenguaje natural.

Reglas:
- Responde SIEMPRE en español.
- Solo lectura: nunca intentes INSERT, UPDATE, DELETE ni DDL. Serán rechazados.
- Los montos están en pesos chilenos; formatéalos con separador de miles (ej: $1.234.567).
- Responde únicamente con datos que hayas obtenido de la base. Si la consulta no devuelve
  filas, dilo explícitamente en vez de inventar una respuesta.
- Si la pregunta es ambigua, elige la interpretación más razonable y explicita cuál usaste.
- Termina tu respuesta citando el SQL exacto que usaste, en una línea que empiece con "SQL: ".
- Sé breve: dos o tres frases, más una lista si hay varios resultados."""


def _herramientas_a_openai(herramientas) -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": h.name,
                "description": h.description or "",
                "parameters": h.inputSchema or {"type": "object", "properties": {}},
            },
        }
        for h in herramientas
    ]


def _texto_de_resultado(resultado) -> str:
    partes = []
    for bloque in resultado.content:
        texto = getattr(bloque, "text", None)
        partes.append(texto if texto is not None else str(bloque))
    return "\n".join(partes)


async def _responder(session: ClientSession, client: AsyncOpenAI, pregunta: str, tools: list[dict]) -> str:
    mensajes: list[dict] = [
        {"role": "system", "content": _PROMPT_SISTEMA},
        {"role": "user", "content": pregunta},
    ]

    for _ in range(_MAX_PASOS):
        respuesta = await client.chat.completions.create(
            model=_MODELO, messages=mensajes, tools=tools, temperature=0,
        )
        mensaje = respuesta.choices[0].message

        if not mensaje.tool_calls:
            return (mensaje.content or "").strip()

        mensajes.append(mensaje.model_dump(exclude_none=True))

        for llamada in mensaje.tool_calls:
            nombre = llamada.function.name
            try:
                argumentos = json.loads(llamada.function.arguments or "{}")
            except json.JSONDecodeError:
                argumentos = {}
            try:
                resultado = await session.call_tool(nombre, argumentos)
                contenido = _texto_de_resultado(resultado)
            except Exception as exc:
                contenido = f"ERROR al ejecutar la herramienta: {type(exc).__name__}: {exc}"

            mensajes.append({"role": "tool", "tool_call_id": llamada.id, "content": contenido})

    return f"No llegué a una respuesta en {_MAX_PASOS} pasos. Reformula la pregunta de forma más específica."


async def _consultar_async(pregunta: str) -> str:
    settings = get_settings()
    parametros = StdioServerParameters(
        command="python", args=[str(_SERVIDOR)], cwd=str(_MCP_DIR),
    )
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    async with stdio_client(parametros) as (lectura, escritura):
        async with ClientSession(lectura, escritura) as session:
            await session.initialize()
            listado = await session.list_tools()
            tools = _herramientas_a_openai(listado.tools)
            return await _responder(session, client, pregunta, tools)


@tool
def consultar_ventas_mad_market(pregunta: str) -> str:
    """Responde preguntas transaccionales/analíticas sobre mad_market consultando
    la base de datos real (clientes, productos, pedidos, detalle_pedidos) vía SQL.
    Usa esta tool para preguntas tipo: qué cliente gastó más, productos más vendidos,
    ventas por canal/ciudad/categoría, estado de pedidos, stock. Un intento de
    escritura (INSERT/UPDATE/DELETE) siempre es rechazado por el servidor: solo lectura.
    """
    try:
        return asyncio.run(_consultar_async(pregunta))
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_consultar_async(pregunta))
        finally:
            loop.close()
    except Exception as exc:  # errores de conexión MCP/OpenAI
        logger.exception("sql_tool falló")
        return f"No pude consultar la base de datos: {type(exc).__name__}: {exc}"
