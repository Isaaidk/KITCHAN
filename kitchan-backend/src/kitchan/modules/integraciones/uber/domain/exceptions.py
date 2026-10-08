"""Errores de negocio de la integración Uber Eats.

La capa de aplicación los lanza sin depender de FastAPI; es el controlador
(infraestructura) quien los traduce a respuestas HTTP.
"""


class UberTokenNoDisponibleError(Exception):
    """No hay App Token de Uber vigente para el restaurante."""


class UberOrdenNoDisponibleError(Exception):
    """Uber no devolvió los detalles de la orden notificada."""
