class RappiOAuthEstadoInvalidoError(Exception):
    """El `state` del retorno de Rappi no existe, expiró o ya se usó."""


class RappiOAuthError(Exception):
    """Rappi rechazó el intercambio del código por el token del comercio."""
