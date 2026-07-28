# -*- coding: utf-8 -*-
"""
Servidor MCP sobre SQLite (transporte stdio).

Expone la base tienda.db como herramientas MCP:
    - listar_tablas()
    - describir_tabla(tabla)
    - esquema_completo()
    - ejecutar_consulta(sql)

El acceso es de SOLO LECTURA: la conexión se abre en modo `ro` y además hay
una validación previa que rechaza cualquier sentencia que no sea SELECT/WITH.

No se ejecuta a mano: lo lanza agent.py por stdio. Para probarlo suelto:
    python servidor_mcp.py          (queda esperando mensajes MCP por stdin)
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from mcp.server.fastmcp import FastMCP

import crear_bd

RUTA_BD = Path(__file__).with_name("tienda.db")
LIMITE_FILAS = 200

# log_level WARNING: en stdio el servidor escribe sus logs por stderr y
# ensucian la salida del agente. Solo queremos ver errores reales.
mcp = FastMCP("sqlite-mad-market", log_level="WARNING")

# Todo lo que no sea consulta de lectura queda fuera.
PALABRAS_PROHIBIDAS = {
    "insert", "update", "delete", "drop", "alter", "create", "replace",
    "truncate", "attach", "detach", "pragma", "vacuum", "reindex", "grant",
}


def _conectar() -> sqlite3.Connection:
    """Conexión de solo lectura. Falla si la base no existe."""
    if not RUTA_BD.exists():
        crear_bd.crear(RUTA_BD)
    con = sqlite3.connect(f"file:{RUTA_BD}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def _validar_sql(sql: str) -> str | None:
    """Devuelve un mensaje de error si el SQL no es una lectura segura."""
    limpio = sql.strip().rstrip(";").strip()
    if not limpio:
        return "La consulta está vacía."

    # Varias sentencias encadenadas: se rechaza.
    if ";" in limpio:
        return "Solo se permite una sentencia por consulta."

    sin_comentarios = re.sub(r"--[^\n]*|/\*.*?\*/", " ", limpio, flags=re.S).lower()

    if not re.match(r"^\s*(select|with)\b", sin_comentarios):
        return "Solo se permiten consultas SELECT o WITH."

    for palabra in PALABRAS_PROHIBIDAS:
        if re.search(rf"\b{palabra}\b", sin_comentarios):
            return f"Palabra no permitida en una consulta de lectura: {palabra.upper()}."

    return None


@mcp.tool()
def listar_tablas() -> str:
    """Lista las tablas disponibles en la base de datos."""
    with _conectar() as con:
        filas = con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
    return "\n".join(f["name"] for f in filas) or "(sin tablas)"


@mcp.tool()
def describir_tabla(tabla: str) -> str:
    """Devuelve las columnas, tipos y una fila de ejemplo de una tabla."""
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", tabla):
        return "Nombre de tabla inválido."

    with _conectar() as con:
        existe = con.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (tabla,)
        ).fetchone()
        if not existe:
            return f"La tabla '{tabla}' no existe."

        columnas = con.execute(f"PRAGMA table_info({tabla})").fetchall()
        total = con.execute(f"SELECT COUNT(*) AS n FROM {tabla}").fetchone()["n"]
        ejemplo = con.execute(f"SELECT * FROM {tabla} LIMIT 1").fetchone()

    lineas = [f"Tabla: {tabla}  ({total} filas)", "Columnas:"]
    lineas += [
        f"  - {c['name']} {c['type']}"
        + (" PRIMARY KEY" if c["pk"] else "")
        + (" NOT NULL" if c["notnull"] else "")
        for c in columnas
    ]
    if ejemplo:
        lineas.append("Fila de ejemplo:")
        lineas.append("  " + ", ".join(f"{k}={ejemplo[k]!r}" for k in ejemplo.keys()))
    return "\n".join(lineas)


@mcp.tool()
def esquema_completo() -> str:
    """Devuelve el CREATE TABLE de todas las tablas. Úsalo antes de escribir SQL."""
    with _conectar() as con:
        filas = con.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
    return "\n\n".join(f["sql"] for f in filas if f["sql"])


@mcp.tool()
def ejecutar_consulta(sql: str) -> str:
    """
    Ejecuta una consulta SELECT de solo lectura y devuelve los resultados.

    Solo se aceptan sentencias SELECT o WITH, una por llamada.
    El resultado se limita a 200 filas.
    """
    error = _validar_sql(sql)
    if error:
        return f"CONSULTA RECHAZADA: {error}"

    try:
        with _conectar() as con:
            cursor = con.execute(sql.strip().rstrip(";"))
            filas = cursor.fetchmany(LIMITE_FILAS)
            columnas = [d[0] for d in cursor.description] if cursor.description else []
    except sqlite3.Error as exc:
        return f"ERROR SQL: {exc}"

    if not filas:
        return "La consulta no devolvió filas."

    salida = [" | ".join(columnas), "-" * 60]
    salida += [" | ".join("" if f[c] is None else str(f[c]) for c in columnas) for f in filas]
    if len(filas) == LIMITE_FILAS:
        salida.append(f"... (truncado en {LIMITE_FILAS} filas)")
    salida.append(f"\n[{len(filas)} fila(s)]")
    return "\n".join(salida)


if __name__ == "__main__":
    crear_bd.crear(RUTA_BD)  # asegura que la base exista antes de atender
    mcp.run(transport="stdio")
