class FacturacionError(Exception):
    """Error base del módulo de facturación."""


class PedidoNoFacturableError(FacturacionError):
    """El pedido no existe, es de otro restaurante o su estado no permite
    facturarlo."""


class PedidoNoEncontradoError(PedidoNoFacturableError):
    """El pedido no existe o es de otro restaurante."""


class OdooNoConfiguradoError(FacturacionError):
    """Faltan las variables de entorno de Odoo."""


class OdooError(FacturacionError):
    """Odoo respondió con un error o no respondió."""
