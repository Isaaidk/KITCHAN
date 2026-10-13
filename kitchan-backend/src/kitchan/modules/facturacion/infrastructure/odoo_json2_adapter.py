"""Adaptador de salida hacia Odoo 19 con la API externa JSON-2
(POST /json/2/<modelo>/<método>, autenticada con una API key).

Se usa JSON-2 y no XML-RPC porque XML-RPC/JSON-RPC están deprecados y se
eliminan en Odoo 22. Cada llamada de JSON-2 corre en su propia transacción
en Odoo, por eso emitir_factura es idempotente: si una llamada falla a mitad
de camino, el siguiente intento encuentra la factura por su referencia y
continúa desde donde quedó, sin crear una segunda.
"""

import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from src.kitchan.modules.facturacion.domain.entities import (
    DatosFactura,
    EstadoFactura,
    ResultadoOdoo,
)
from src.kitchan.modules.facturacion.domain.exceptions import (
    OdooError,
    OdooNoConfiguradoError,
)
from src.kitchan.modules.facturacion.domain.ports import OdooFacturacionPort

logger = logging.getLogger(__name__)

CAMPOS_FACTURA = [
    "name",
    "state",
    "amount_total",
    "edi_state",
    "edi_error_message",
    "edi_blocking_level",
    "l10n_ec_authorization_number",
    "l10n_ec_authorization_date",
]


def _entero(variable: str) -> Optional[int]:
    valor = os.getenv(variable)
    return int(valor) if valor else None


def _texto_plano(html: Any) -> Optional[str]:
    if not html:
        return None
    texto = re.sub(r"<[^>]+>", " ", str(html))
    return re.sub(r"\s+", " ", texto).strip() or None


def _fecha(valor: Any) -> Optional[datetime]:
    if not valor:
        return None
    # Odoo entrega las fechas en UTC y sin zona horaria.
    return datetime.fromisoformat(str(valor)).replace(tzinfo=timezone.utc)


def a_resultado(factura: dict) -> ResultadoOdoo:
    """Traduce una factura leída de Odoo al estado que maneja KITCHAN."""
    mensaje = _texto_plano(factura.get("edi_error_message"))
    edi_state = factura.get("edi_state")

    if factura.get("state") == "cancel" or edi_state in ("to_cancel", "cancelled"):
        estado = EstadoFactura.ANULADA
    elif factura.get("state") != "posted":
        estado = EstadoFactura.CON_ERROR
        mensaje = mensaje or "La factura quedó en borrador en Odoo."
    elif edi_state == "sent":
        estado = EstadoFactura.AUTORIZADA
    elif factura.get("edi_blocking_level") == "error":
        estado = EstadoFactura.CON_ERROR
    else:
        estado = EstadoFactura.PENDIENTE_SRI

    return ResultadoOdoo(
        odoo_move_id=factura["id"],
        numero=factura.get("name") or None,
        estado=estado,
        total=float(factura.get("amount_total") or 0),
        numero_autorizacion=factura.get("l10n_ec_authorization_number") or None,
        fecha_autorizacion=_fecha(factura.get("l10n_ec_authorization_date")),
        mensaje_error=None if estado == EstadoFactura.AUTORIZADA else mensaje,
    )


class OdooJson2Adapter(OdooFacturacionPort):
    def __init__(self, http_client: Optional[httpx.AsyncClient] = None):
        self.url = (os.getenv("ODOO_URL") or "").rstrip("/")
        self.db = os.getenv("ODOO_DB")
        self.api_key = os.getenv("ODOO_API_KEY")
        # Registros de Odoo con los que se arma la factura (ver .env.example).
        self.diario_id = _entero("ODOO_DIARIO_ID")
        self.cliente_id = _entero("ODOO_CLIENTE_ID")
        self.producto_id = _entero("ODOO_PRODUCTO_ID")
        self.impuesto_id = _entero("ODOO_IMPUESTO_ID")
        self.pago_sri_id = _entero("ODOO_PAGO_SRI_ID")
        self.http_client = http_client
        self._porcentaje_iva: Optional[float] = None

    def configurado(self) -> bool:
        return all(
            [
                self.url,
                self.api_key,
                self.diario_id,
                self.cliente_id,
                self.producto_id,
                self.impuesto_id,
                self.pago_sri_id,
            ]
        )

    async def _post(self, url: str, parametros: dict, headers: dict) -> httpx.Response:
        if self.http_client is not None:
            return await self.http_client.post(
                url, json=parametros, headers=headers, timeout=30
            )
        async with httpx.AsyncClient() as cliente:
            return await cliente.post(url, json=parametros, headers=headers, timeout=30)

    async def _llamar(self, modelo: str, metodo: str, **parametros) -> Any:
        if not self.configurado():
            raise OdooNoConfiguradoError("Odoo no está configurado en KITCHAN.")
        headers = {"Authorization": f"bearer {self.api_key}", "User-Agent": "KITCHAN"}
        if self.db:
            headers["X-Odoo-Database"] = self.db
        try:
            respuesta = await self._post(
                f"{self.url}/json/2/{modelo}/{metodo}", parametros, headers
            )
        except httpx.HTTPError as error:
            logger.warning("Odoo no respondió a %s.%s: %s", modelo, metodo, error)
            raise OdooError("Odoo no respondió. Intenta de nuevo en unos minutos.")

        if respuesta.status_code >= 400:
            try:
                mensaje = respuesta.json().get("message")
            except ValueError:
                mensaje = None
            logger.warning(
                "Odoo respondió %s a %s.%s: %s",
                respuesta.status_code,
                modelo,
                metodo,
                mensaje,
            )
            if respuesta.status_code in (401, 403):
                raise OdooError(
                    "Odoo rechazó la API key de KITCHAN. Revisa ODOO_API_KEY."
                )
            raise OdooError(f"Odoo respondió: {mensaje or respuesta.status_code}")
        # Los métodos que no devuelven nada pueden responder sin cuerpo.
        return respuesta.json() if respuesta.content else None

    async def _iva(self) -> float:
        if self._porcentaje_iva is None:
            impuesto = await self._llamar(
                "account.tax", "read", ids=[self.impuesto_id], fields=["amount"]
            )
            self._porcentaje_iva = float(impuesto[0]["amount"])
        return self._porcentaje_iva

    async def _leer(self, odoo_move_id: int) -> dict:
        facturas = await self._llamar(
            "account.move", "read", ids=[odoo_move_id], fields=CAMPOS_FACTURA
        )
        if not facturas:
            raise OdooError(f"La factura {odoo_move_id} ya no existe en Odoo.")
        return facturas[0]

    async def _enviar_al_sri(self, odoo_move_id: int) -> ResultadoOdoo:
        """Pide a Odoo enviar la factura (ya publicada) al SRI y devuelve su
        estado. Los rechazos del SRI quedan registrados en la factura, pero
        si Odoo falla antes de llegar al SRI (p. ej. no puede firmar con el
        certificado) solo lo dice en la respuesta: se muestra como error
        para que se pueda corregir y reintentar."""
        try:
            await self._llamar(
                "account.move", "action_process_edi_web_services", ids=[odoo_move_id]
            )
            error = None
        except OdooError as fallo:
            logger.warning("Envío al SRI de la factura %s: %s", odoo_move_id, fallo)
            error = str(fallo)

        resultado = a_resultado(await self._leer(odoo_move_id))
        if error and resultado.estado == EstadoFactura.PENDIENTE_SRI:
            return resultado.model_copy(
                update={
                    "estado": EstadoFactura.CON_ERROR,
                    "mensaje_error": f"Odoo no pudo enviar la factura al SRI. {error}",
                }
            )
        return resultado

    async def _crear_borrador(self, datos: DatosFactura) -> int:
        iva = await self._iva()
        lineas = [
            [
                0,
                0,
                {
                    "product_id": self.producto_id,
                    "name": linea.descripcion,
                    "quantity": linea.cantidad,
                    # Las plataformas cobran con IVA incluido; Odoo espera el
                    # precio unitario sin IVA.
                    "price_unit": round(linea.precio_con_iva / (1 + iva / 100), 2),
                    "tax_ids": [[6, 0, [self.impuesto_id]]],
                },
            ]
            for linea in datos.lineas
        ]
        ids = await self._llamar(
            "account.move",
            "create",
            vals_list=[
                {
                    "move_type": "out_invoice",
                    "journal_id": self.diario_id,
                    "partner_id": self.cliente_id,
                    "l10n_ec_sri_payment_id": self.pago_sri_id,
                    "ref": datos.referencia,
                    "invoice_origin": datos.origen,
                    "invoice_line_ids": lineas,
                }
            ],
        )
        return ids[0]

    async def emitir_factura(self, datos: DatosFactura) -> ResultadoOdoo:
        existentes = await self._llamar(
            "account.move",
            "search_read",
            domain=[
                ["ref", "=", datos.referencia],
                ["move_type", "=", "out_invoice"],
                ["state", "!=", "cancel"],
            ],
            fields=["state"],
            limit=1,
        )
        if existentes:
            move_id, estado = existentes[0]["id"], existentes[0]["state"]
        else:
            move_id, estado = await self._crear_borrador(datos), "draft"

        if estado == "draft":
            await self._llamar("account.move", "action_post", ids=[move_id])
        return await self._enviar_al_sri(move_id)

    async def consultar_factura(self, odoo_move_id: int) -> ResultadoOdoo:
        return a_resultado(await self._leer(odoo_move_id))

    async def reenviar_al_sri(self, odoo_move_id: int) -> ResultadoOdoo:
        return await self._enviar_al_sri(odoo_move_id)
