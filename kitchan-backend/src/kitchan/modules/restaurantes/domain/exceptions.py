"""Excepciones de dominio del módulo Restaurantes.

Permiten que la capa de aplicación reaccione a reglas de negocio (por ejemplo,
un RUC ya registrado) sin conocer la base de datos: es el repositorio quien
traduce los errores técnicos de SQLAlchemy a estas excepciones.
"""


class RegistroDuplicadoError(ValueError):
    """El restaurante o su administrador ya existen (RUC o email repetidos).

    Hereda de ValueError para que la API lo siga respondiendo como 400.
    """
