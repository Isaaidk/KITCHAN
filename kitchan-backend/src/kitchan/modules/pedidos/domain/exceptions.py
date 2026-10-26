class PedidoDuplicadoError(Exception):
    """Ya existe un pedido de esa plataforma con el mismo id externo.

    Las plataformas pueden reenviar un webhook (reintentos, timeouts), así que
    el mismo pedido no debe crearse dos veces.
    """
