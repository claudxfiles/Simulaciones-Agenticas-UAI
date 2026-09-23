"""Validación de sesión Supabase para proteger /api/agent e /api/insights.

Reusa el mismo patrón de dukeagent: el frontend adjunta el access_token
de Supabase Auth como Bearer, y acá se valida contra
GET {SUPABASE_URL}/auth/v1/user en cada request (sin verificar JWT
localmente — más simple, un solo usuario permitido).
"""
import httpx
from fastapi import Header, HTTPException

from app.config import get_settings


async def require_auth(authorization: str | None = Header(default=None)) -> str:
    settings = get_settings()
    if not settings.supabase_url or not settings.allowed_email:
        # Auth no configurada (dev local) — no bloquear.
        return "anonymous"

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No autenticado")

    token = authorization.removeprefix("Bearer ").strip()
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(
            f"{settings.supabase_url}/auth/v1/user",
            headers={"Authorization": f"Bearer {token}", "apikey": settings.supabase_anon_key},
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Sesión inválida")

    email = resp.json().get("email")
    if email != settings.allowed_email:
        raise HTTPException(status_code=403, detail="Usuario no autorizado")
    return email
