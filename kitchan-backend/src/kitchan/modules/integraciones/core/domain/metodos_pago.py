"""Normalización del método de pago que informa cada canal.

Cada plataforma usa sus propios códigos ("cc", "cash", ...). Aquí se traducen a
un vocabulario común para que Reportes pueda sumar métodos de pago entre canales.
Si el canal no informa el método, el resultado es None: nunca se inventa uno.
"""

from typing import Optional

EFECTIVO = "EFECTIVO"
TARJETA = "TARJETA"
TRANSFERENCIA = "TRANSFERENCIA"
BILLETERA = "BILLETERA"
ONLINE = "ONLINE"

_EQUIVALENCIAS = {
    # Efectivo
    "cash": EFECTIVO,
    "efectivo": EFECTIVO,
    "money": EFECTIVO,
    # Tarjeta (crédito o débito)
    "cc": TARJETA,
    "credit": TARJETA,
    "credit_card": TARJETA,
    "creditcard": TARJETA,
    "debit": TARJETA,
    "debit_card": TARJETA,
    "card": TARJETA,
    "tarjeta": TARJETA,
    # Transferencia
    "transfer": TRANSFERENCIA,
    "bank_transfer": TRANSFERENCIA,
    "transferencia": TRANSFERENCIA,
    # Billetera digital
    "wallet": BILLETERA,
    "rappi_pay": BILLETERA,
    "rappipay": BILLETERA,
    "billetera": BILLETERA,
    # Pagado en la aplicación de la plataforma
    "online": ONLINE,
    "app": ONLINE,
    "prepaid": ONLINE,
}


def normalizar_metodo_pago(valor: Optional[str]) -> Optional[str]:
    """Devuelve el método en el vocabulario común, o None si no hay dato.

    Un código desconocido se conserva en mayúsculas (sin inventar su significado)
    para que el administrador lo vea en las analíticas.
    """
    if valor is None:
        return None
    limpio = str(valor).strip()
    if not limpio:
        return None
    clave = limpio.casefold().replace("-", "_").replace(" ", "_")
    return _EQUIVALENCIAS.get(clave, clave.upper()[:30])
