class RappiOAuthEstadoInvalidoError(Exception):
    """El `state` del retorno de Rappi no existe, expiró o ya se usó."""


class RappiOAuthError(Exception):
    """Rappi rechazó el intercambio del código por el token del comercio."""


class RappiAccionNoConfirmadaError(Exception):
    """Rappi respondió con error a una acción opcional (p. ej. "listo para
    recoger"): el pedido puede seguir su curso en KITCHAN sin esa confirmación."""

    def __init__(self, accion: str, estado: int, detalle: str = ""):
        super().__init__(f"Rappi no confirmó '{accion}' ({estado}).")
        self.accion = accion
        self.estado = estado
        self.detalle = detalle
