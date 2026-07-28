"""Tool: analizar_accion — delega en el sub-agente de investigación bursátil.

Adaptado de madxerax-agents/agent-stock-research/agent.py: mismos
get_stock_data/analyze_stock (Yahoo Finance + LLM), sin la capa CLI del
script original. Incluye un reintento ante fallos transitorios de red/API,
como pide el paso 04 del roadmap (manejo de errores y reintentos).
"""
from __future__ import annotations

import logging
import time

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

_MODEL = "gpt-4o-mini"

_DISCLAIMER = (
    "Herramienta educativa. Este resumen lo genera un modelo de lenguaje a partir "
    "de datos públicos con retraso y NO es asesoría de inversión. Verifica cada "
    "cifra contra una fuente primaria antes de tomar cualquier decisión financiera."
)

_ANALYST_PROMPT = """You are a financial analyst. Provide a concise stock analysis covering:
Investment Thesis (2-3 sentences), Key Strengths (3 bullets), Key Risks (3 bullets),
Valuation Assessment, and a Verdict (Buy/Hold/Sell with brief reasoning).
Keep it under 300 words. Responde en español.

Rules:
- Use ONLY the figures provided. Do not invent metrics, prices or events.
- If a field says "N/A", treat it as unknown and say so rather than guessing.
- The data is a point-in-time snapshot and may be delayed; do not claim it is live.
- State clearly that this is not investment advice."""

_CAMPOS_FRACCION = {"revenue_growth", "profit_margin"}


def _get_stock_data(ticker: str) -> dict:
    import yfinance as yf

    info = yf.Ticker(ticker).info or {}
    price = info.get("currentPrice") or info.get("regularMarketPrice")
    if not info.get("longName") and price is None:
        raise RuntimeError(
            f"'{ticker}' no devolvió datos de Yahoo Finance. Revisa el símbolo "
            "(ej: AAPL, NVDA, MSFT). Mercados no-US necesitan sufijo, ej: FALABELLA.SN."
        )

    return {
        "ticker": ticker.upper(),
        "name": info.get("longName") or ticker.upper(),
        "currency": info.get("currency") or "USD",
        "sector": info.get("sector") or "N/A",
        "industry": info.get("industry") or "N/A",
        "price": price if price is not None else "N/A",
        "market_cap": info.get("marketCap") or "N/A",
        "pe_ratio": info.get("trailingPE") or "N/A",
        "forward_pe": info.get("forwardPE") or "N/A",
        "peg_ratio": info.get("pegRatio") or "N/A",
        "revenue_growth": info.get("revenueGrowth", "N/A"),
        "profit_margin": info.get("profitMargins", "N/A"),
        "dividend_yield": info.get("dividendYield", "N/A"),
        "52w_high": info.get("fiftyTwoWeekHigh") or "N/A",
        "52w_low": info.get("fiftyTwoWeekLow") or "N/A",
        "analyst_rating": info.get("recommendationKey") or "N/A",
        "target_price": info.get("targetMeanPrice") or "N/A",
        "description": (info.get("longBusinessSummary") or "")[:500],
    }


def _format_number(n, moneda: str | None = None) -> str:
    if not isinstance(n, (int, float)) or isinstance(n, bool):
        return str(n)
    es_usd = moneda in (None, "USD")
    simbolo = "$" if es_usd else ""
    codigo = "" if es_usd else f" {moneda}"
    signo = "-" if n < 0 else ""
    valor = abs(n)
    for umbral, sufijo in ((1e12, "T"), (1e9, "B"), (1e6, "M")):
        if valor >= umbral:
            return f"{signo}{simbolo}{valor / umbral:.2f}{sufijo}{codigo}"
    return f"{signo}{simbolo}{valor:,.2f}{codigo}"


def _format_ratio(n) -> str:
    if not isinstance(n, (int, float)) or isinstance(n, bool):
        return str(n)
    return f"{n:.2f}"


def _format_percent(n, es_fraccion: bool) -> str:
    if not isinstance(n, (int, float)) or isinstance(n, bool):
        return str(n)
    return f"{n * 100:.2f}%" if es_fraccion else f"{n:.2f}%"


def _datos_legibles(data: dict) -> dict:
    legible: dict[str, str] = {}
    for clave, valor in data.items():
        if clave == "description":
            continue
        if clave in ("market_cap", "price", "target_price", "52w_high", "52w_low"):
            legible[clave] = _format_number(valor, data.get("currency"))
        elif clave in ("pe_ratio", "forward_pe", "peg_ratio"):
            legible[clave] = _format_ratio(valor)
        elif clave in ("revenue_growth", "profit_margin", "dividend_yield"):
            legible[clave] = _format_percent(valor, clave in _CAMPOS_FRACCION)
        else:
            legible[clave] = str(valor)
    return legible


def _analyze_stock(data: dict) -> str:
    from app.infrastructure.llm.client import get_chat_model

    llm = get_chat_model()
    stock_info = "\n".join(f"{k}: {v}" for k, v in _datos_legibles(data).items())
    response = llm.invoke([
        SystemMessage(content=_ANALYST_PROMPT),
        HumanMessage(content=(
            f"Analyze this stock:\n{stock_info}\n\n"
            f"Company description: {data.get('description') or 'N/A'}"
        )),
    ])
    return str(response.content).strip()


def _con_reintento(func, *args, intentos: int = 2, espera_s: float = 1.5):
    ultimo_error: Exception | None = None
    for intento in range(intentos):
        try:
            return func(*args)
        except Exception as exc:
            ultimo_error = exc
            logger.warning("stock_tool intento %d/%d falló: %s", intento + 1, intentos, exc)
            if intento < intentos - 1:
                time.sleep(espera_s)
    raise ultimo_error  # type: ignore[misc]


@tool
def analizar_accion(ticker: str) -> str:
    """Investiga una acción bursátil (no relacionada con mad_market): precio,
    capitalización, ratios (P/E, PEG), crecimiento, margen, dividendo, rango 52
    semanas, y un análisis de inversión generado por IA. Usa esta tool cuando el
    usuario pregunte por una empresa que cotiza en bolsa o un ticker (ej: AAPL,
    NVDA, FALABELLA.SN). No es asesoría financiera.
    """
    ticker_limpio = ticker.strip().strip('"').strip("'").upper()
    try:
        data = _con_reintento(_get_stock_data, ticker_limpio)
    except Exception as exc:
        return f"No pude obtener datos de '{ticker_limpio}': {type(exc).__name__}: {exc}"

    try:
        analysis = _con_reintento(_analyze_stock, data)
    except Exception as exc:
        logger.exception("análisis LLM de stock falló")
        analysis = f"(análisis no disponible: {type(exc).__name__}: {exc})"

    ficha = _datos_legibles(data)
    resumen = (
        f"{data['name']} ({data['ticker']}) — Precio: {ficha['price']} | "
        f"Cap: {ficha['market_cap']} | P/E: {ficha['pe_ratio']} | "
        f"Analista: {ficha['analyst_rating']}\n\n{analysis}\n\n{_DISCLAIMER}"
    )
    return resumen
