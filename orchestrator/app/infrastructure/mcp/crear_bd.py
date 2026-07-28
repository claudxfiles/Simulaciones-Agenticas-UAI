# -*- coding: utf-8 -*-
"""
Crea y puebla la base SQLite de ejemplo: mad_market (retail).

Se ejecuta solo, o lo llama el servidor MCP si la base todavía no existe.

    python crear_bd.py            # crea tienda.db
    python crear_bd.py --recrear  # la borra y la vuelve a crear
"""

from __future__ import annotations

import argparse
import sqlite3
from datetime import date, timedelta
from pathlib import Path

RUTA_BD = Path(__file__).with_name("tienda.db")

ESQUEMA = """
CREATE TABLE clientes (
    id            INTEGER PRIMARY KEY,
    nombre        TEXT    NOT NULL,
    ciudad        TEXT    NOT NULL,
    segmento      TEXT    NOT NULL,  -- retail | mayorista | corporativo
    fecha_alta    TEXT    NOT NULL
);

CREATE TABLE productos (
    id            INTEGER PRIMARY KEY,
    nombre        TEXT    NOT NULL,
    categoria     TEXT    NOT NULL,  -- tecnologia | hogar | vestuario | deportes
    precio        REAL    NOT NULL,
    stock         INTEGER NOT NULL
);

CREATE TABLE pedidos (
    id            INTEGER PRIMARY KEY,
    cliente_id    INTEGER NOT NULL REFERENCES clientes(id),
    fecha         TEXT    NOT NULL,
    canal         TEXT    NOT NULL,  -- web | app | tienda | telefono
    estado        TEXT    NOT NULL,  -- entregado | en_transito | preparacion | cancelado
    total         REAL    NOT NULL
);

CREATE TABLE detalle_pedidos (
    id            INTEGER PRIMARY KEY,
    pedido_id     INTEGER NOT NULL REFERENCES pedidos(id),
    producto_id   INTEGER NOT NULL REFERENCES productos(id),
    cantidad      INTEGER NOT NULL,
    precio_unit   REAL    NOT NULL
);

CREATE INDEX idx_pedidos_cliente ON pedidos(cliente_id);
CREATE INDEX idx_detalle_pedido  ON detalle_pedidos(pedido_id);
"""

CLIENTES = [
    (1,  "Camila Rojas",     "Santiago",     "retail",      "2024-03-11"),
    (2,  "Diego Fuentes",    "Valparaíso",   "retail",      "2024-05-02"),
    (3,  "Comercial Andes",  "Santiago",     "mayorista",   "2023-11-20"),
    (4,  "Fernanda Silva",   "Concepción",   "retail",      "2025-01-15"),
    (5,  "Grupo Patagonia",  "Puerto Montt", "corporativo", "2023-08-04"),
    (6,  "Matías Herrera",   "Santiago",     "retail",      "2025-06-30"),
    (7,  "Valentina Núñez",  "La Serena",    "retail",      "2024-09-18"),
    (8,  "Distribuidora Sur","Temuco",       "mayorista",   "2024-02-27"),
    (9,  "Ignacio Bravo",    "Antofagasta",  "retail",      "2025-04-09"),
    (10, "Paula Contreras",  "Santiago",     "corporativo", "2024-07-22"),
]

PRODUCTOS = [
    (1,  "Notebook Aurora 14\"",   "tecnologia", 749990.0, 24),
    (2,  "Audífonos Bluetooth Z2", "tecnologia",  39990.0, 180),
    (3,  "Monitor 27\" QHD",       "tecnologia", 229990.0, 12),
    (4,  "Hervidor eléctrico 1.7L","hogar",       24990.0, 95),
    (5,  "Aspiradora robot Mini",  "hogar",      189990.0, 8),
    (6,  "Set de sábanas king",    "hogar",       34990.0, 60),
    (7,  "Polera algodón básica",  "vestuario",    9990.0, 320),
    (8,  "Parka impermeable",      "vestuario",   79990.0, 45),
    (9,  "Zapatillas running Trek","deportes",    64990.0, 70),
    (10, "Mancuernas 10kg par",    "deportes",    44990.0, 30),
    (11, "Bicicleta urbana Aro 28","deportes",   329990.0, 6),
    (12, "Teclado mecánico RGB",   "tecnologia",  59990.0, 52),
]

# (id, cliente_id, dias_atras, canal, estado, [(producto_id, cantidad), ...])
PEDIDOS = [
    (1,  1,  95, "web",      "entregado",    [(2, 1), (7, 3)]),
    (2,  1,  62, "app",      "entregado",    [(4, 1)]),
    (3,  2,  88, "tienda",   "entregado",    [(9, 1), (10, 1)]),
    (4,  3,  80, "telefono", "entregado",    [(7, 40), (2, 15)]),
    (5,  4,  74, "web",      "cancelado",    [(3, 1)]),
    (6,  5,  70, "telefono", "entregado",    [(1, 6), (3, 6)]),
    (7,  6,  58, "app",      "entregado",    [(2, 2)]),
    (8,  7,  51, "web",      "entregado",    [(8, 1), (6, 1)]),
    (9,  2,  47, "app",      "en_transito",  [(12, 1)]),
    (10, 8,  44, "telefono", "entregado",    [(4, 25), (6, 20)]),
    (11, 9,  40, "web",      "entregado",    [(11, 1)]),
    (12, 10, 36, "tienda",   "entregado",    [(1, 3), (12, 3)]),
    (13, 1,  30, "web",      "entregado",    [(5, 1)]),
    (14, 4,  27, "app",      "entregado",    [(7, 2), (9, 1)]),
    (15, 3,  22, "telefono", "en_transito",  [(2, 30)]),
    (16, 6,  18, "web",      "preparacion",  [(3, 1), (12, 1)]),
    (17, 7,  15, "tienda",   "entregado",    [(4, 1), (6, 2)]),
    (18, 5,  12, "telefono", "entregado",    [(1, 4)]),
    (19, 9,   9, "app",      "cancelado",    [(8, 1)]),
    (20, 10,  7, "web",      "en_transito",  [(5, 2), (10, 2)]),
    (21, 2,   5, "app",      "preparacion",  [(9, 1)]),
    (22, 8,   3, "telefono", "en_transito",  [(7, 60)]),
    (23, 1,   2, "web",      "preparacion",  [(2, 1), (12, 1)]),
    (24, 4,   1, "tienda",   "entregado",    [(6, 1)]),
]


def crear(ruta: Path = RUTA_BD, recrear: bool = False) -> Path:
    """Crea la base con datos de ejemplo. Devuelve la ruta."""
    if ruta.exists():
        if not recrear:
            return ruta
        ruta.unlink()

    precios = {p[0]: p[3] for p in PRODUCTOS}
    hoy = date.today()

    con = sqlite3.connect(ruta)
    try:
        con.executescript(ESQUEMA)
        con.executemany("INSERT INTO clientes VALUES (?,?,?,?,?)", CLIENTES)
        con.executemany("INSERT INTO productos VALUES (?,?,?,?,?)", PRODUCTOS)

        detalle_id = 0
        for pedido_id, cliente_id, dias, canal, estado, lineas in PEDIDOS:
            fecha = (hoy - timedelta(days=dias)).isoformat()
            total = round(sum(precios[pid] * cant for pid, cant in lineas), 2)
            con.execute(
                "INSERT INTO pedidos VALUES (?,?,?,?,?,?)",
                (pedido_id, cliente_id, fecha, canal, estado, total),
            )
            for producto_id, cantidad in lineas:
                detalle_id += 1
                con.execute(
                    "INSERT INTO detalle_pedidos VALUES (?,?,?,?,?)",
                    (detalle_id, pedido_id, producto_id, cantidad, precios[producto_id]),
                )
        con.commit()
    finally:
        con.close()

    return ruta


def main() -> int:
    p = argparse.ArgumentParser(description="Crea la base SQLite de ejemplo")
    p.add_argument("--recrear", action="store_true", help="Borrar y volver a crear la base")
    args = p.parse_args()

    existia = RUTA_BD.exists()
    crear(RUTA_BD, recrear=args.recrear)

    con = sqlite3.connect(RUTA_BD)
    filas = {
        tabla: con.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
        for tabla in ("clientes", "productos", "pedidos", "detalle_pedidos")
    }
    con.close()

    accion = "recreada" if args.recrear else ("ya existía" if existia else "creada")
    print(f"Base {accion}: {RUTA_BD}")
    for tabla, n in filas.items():
        print(f"  {tabla:<16} {n:>4} filas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
