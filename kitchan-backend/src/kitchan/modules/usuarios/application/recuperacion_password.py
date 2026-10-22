"""Recuperación de contraseña con un código de 6 dígitos enviado al correo.

Flujo: solicitar (se envía el código) → verificar (el código válido se cambia por
un token de restablecimiento de vida corta) → restablecer (token + contraseña nueva).

Por seguridad el código se guarda solo como hash, vence en pocos minutos, admite
un número limitado de intentos y se consume al restablecer. Solicitar nunca revela
si el correo existe.
"""

import hashlib
import hmac
import logging
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional

from src.kitchan.core.security import (
    crear_token_restablecimiento,
    decodificar_token_restablecimiento,
)
from src.kitchan.modules.usuarios.application.ports import (
    ICodigosRecuperacionRepository,
    IEnviadorCorreo,
    IPasswordHasher,
    IUsuarioRepository,
)
from src.kitchan.modules.usuarios.domain.entities import CodigoRecuperacion

logger = logging.getLogger(__name__)

MINUTOS_VALIDEZ_CODIGO = 10
MINUTOS_VALIDEZ_TOKEN = 10
MAX_INTENTOS = 5
# Mínimo entre dos solicitudes del mismo usuario (evita usar el correo para spam).
SEGUNDOS_ENTRE_SOLICITUDES = 60
LARGO_MINIMO_PASSWORD = 8
PROPOSITO_TOKEN = "restablecer_password"

MENSAJE_CODIGO_INVALIDO = "El código no es válido o ya venció"


def _ahora_utc() -> datetime:
    return datetime.now(timezone.utc)


def _como_utc(fecha: datetime) -> datetime:
    # Algunas bases devuelven fechas sin zona; todas se guardan en UTC.
    return fecha if fecha.tzinfo else fecha.replace(tzinfo=timezone.utc)


def _hash_codigo(usuario_id: str, codigo: str) -> str:
    clave = (os.getenv("SECRET_KEY") or "").encode("utf-8")
    return hmac.new(clave, f"{usuario_id}:{codigo}".encode("utf-8"), hashlib.sha256).hexdigest()


class SolicitarRecuperacionUseCase:
    def __init__(
        self,
        usuarios: IUsuarioRepository,
        codigos: ICodigosRecuperacionRepository,
        correo: IEnviadorCorreo,
        ahora: Callable[[], datetime] = _ahora_utc,
    ):
        self.usuarios = usuarios
        self.codigos = codigos
        self.correo = correo
        self.ahora = ahora

    async def ejecutar(self, email: str) -> bool:
        """Devuelve si se generó un código. El endpoint público lo ignora y responde
        siempre igual (exista o no el correo); un administrador sí necesita saberlo."""
        usuario = await self.usuarios.buscar_por_email(email)
        if usuario is None or not usuario.estado:
            return False

        ahora = self.ahora()
        ultimo = await self.codigos.ultimo_de_usuario(usuario.id)
        if ultimo and ahora - _como_utc(ultimo.creado_en) < timedelta(
            seconds=SEGUNDOS_ENTRE_SOLICITUDES
        ):
            return False

        codigo = f"{secrets.randbelow(10**6):06d}"
        await self.codigos.invalidar_de_usuario(usuario.id)
        await self.codigos.crear(
            CodigoRecuperacion(
                id=str(uuid.uuid4()),
                usuario_id=usuario.id,
                codigo_hash=_hash_codigo(usuario.id, codigo),
                expira_en=ahora + timedelta(minutes=MINUTOS_VALIDEZ_CODIGO),
                creado_en=ahora,
            )
        )
        try:
            await self.correo.enviar_codigo_recuperacion(
                usuario.email, usuario.nombre, codigo, MINUTOS_VALIDEZ_CODIGO
            )
        except Exception:
            # El error se registra pero no se muestra: si no, se sabría que el correo existe.
            logger.exception("No se pudo enviar el código de recuperación")
        return True


class VerificarCodigoRecuperacionUseCase:
    def __init__(
        self,
        usuarios: IUsuarioRepository,
        codigos: ICodigosRecuperacionRepository,
        ahora: Callable[[], datetime] = _ahora_utc,
    ):
        self.usuarios = usuarios
        self.codigos = codigos
        self.ahora = ahora

    async def ejecutar(self, email: str, codigo: str) -> str:
        """Devuelve el token de restablecimiento si el código es correcto."""
        usuario = await self.usuarios.buscar_por_email(email)
        if usuario is None or not usuario.estado:
            raise ValueError(MENSAJE_CODIGO_INVALIDO)

        vigente = await self.codigos.ultimo_de_usuario(usuario.id)
        if (
            vigente is None
            or vigente.usado
            or vigente.intentos >= MAX_INTENTOS
            or _como_utc(vigente.expira_en) <= self.ahora()
        ):
            raise ValueError(MENSAJE_CODIGO_INVALIDO)

        esperado = _hash_codigo(usuario.id, codigo.strip())
        if not hmac.compare_digest(esperado, vigente.codigo_hash):
            await self.codigos.registrar_intento_fallido(vigente.id)
            raise ValueError(MENSAJE_CODIGO_INVALIDO)

        return crear_token_restablecimiento(
            {"sub": usuario.email, "cid": vigente.id, "proposito": PROPOSITO_TOKEN},
            MINUTOS_VALIDEZ_TOKEN,
        )


class RestablecerPasswordUseCase:
    def __init__(
        self,
        usuarios: IUsuarioRepository,
        codigos: ICodigosRecuperacionRepository,
        hasher: IPasswordHasher,
        ahora: Callable[[], datetime] = _ahora_utc,
    ):
        self.usuarios = usuarios
        self.codigos = codigos
        self.hasher = hasher
        self.ahora = ahora

    async def ejecutar(self, token: str, nueva_password: str) -> None:
        if len(nueva_password) < LARGO_MINIMO_PASSWORD:
            raise ValueError(
                f"La contraseña debe tener al menos {LARGO_MINIMO_PASSWORD} caracteres"
            )

        claims = decodificar_token_restablecimiento(token)
        if claims.get("proposito") != PROPOSITO_TOKEN:
            raise ValueError("El enlace de restablecimiento no es válido o ya venció")

        codigo: Optional[CodigoRecuperacion] = await self.codigos.buscar_por_id(
            claims.get("cid", "")
        )
        usuario = await self.usuarios.buscar_por_email(claims.get("sub", ""))
        if (
            codigo is None
            or usuario is None
            or not usuario.estado
            or codigo.usado
            or codigo.usuario_id != usuario.id
            or _como_utc(codigo.expira_en) <= self.ahora()
        ):
            raise ValueError("El enlace de restablecimiento no es válido o ya venció")

        # El código se consume primero: el mismo token no sirve dos veces.
        await self.codigos.marcar_usado(codigo.id)
        await self.usuarios.editar_contraseña(
            usuario.email, self.hasher.hashear(nueva_password)
        )
