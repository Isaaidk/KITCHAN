"""Utilidades del simulador de WhatsApp: firma y tienda por defecto, con el mismo
esquema que usa el bot real para llamar al webhook de KITCHAN
(`X-Kitchan-Signature: t=<unix>,sign=<hex>`, HMAC-SHA256 de "<t>.<body>").
"""

import hashlib
import hmac
import json
import os
import time

HEADER = "X-Kitchan-Signature"


def _firmar(secret: str, body: bytes) -> str:
    t = str(int(time.time()))
    sign = hmac.new(
        secret.encode("utf-8"), t.encode() + b"." + body, hashlib.sha256
    ).hexdigest()
    return f"t={t},sign={sign}"


def _store_id_por_defecto() -> str:
    """Primer store_id de WHATSAPP_STORE_ID_MAP (p. ej. "default")."""
    try:
        mapa = json.loads(os.getenv("WHATSAPP_STORE_ID_MAP", "{}"))
    except json.JSONDecodeError:
        mapa = {}
    return next(iter(mapa), "default")
