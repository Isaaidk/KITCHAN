import pytest
from unittest.mock import AsyncMock, MagicMock
from src.kitchan.modules.usuarios.application.use_cases import CrearUsuarioUseCase
from src.kitchan.modules.usuarios.domain.entities import Usuario, RolUsuario


@pytest.mark.anyio
async def test_crear_usuario_exitoso():
    # Arrange
    repositorio_mock = AsyncMock()
    repositorio_mock.buscar_por_email.return_value = None

    async def side_effect(usuario: Usuario):
        return usuario

    repositorio_mock.guardar.side_effect = side_effect

    # Mock del hasher (No es asíncrono, usamos MagicMock)
    hasher_mock = MagicMock()
    hasher_mock.hashear.return_value = "$2b$12$simulacion_de_hash_seguro"

    caso_uso = CrearUsuarioUseCase(repository=repositorio_mock, hasher=hasher_mock)

    # Act
    resultado = await caso_uso.ejecutar(
        nombre="Paulo",
        email="paulo@example.com",
        password_hash="Pauloolivo",
        rol=RolUsuario.ADMIN,
    )

    # Assert
    assert resultado is not None
    assert resultado.nombre == "Paulo"
    assert resultado.email == "paulo@example.com"
    # Verificamos que la entidad recibió el HASH y no el texto plano
    assert resultado.password_hash == "$2b$12$simulacion_de_hash_seguro"

    hasher_mock.hashear.assert_called_once_with("Pauloolivo")
    repositorio_mock.guardar.assert_awaited_once()


@pytest.mark.anyio
async def test_crear_usuario_email_duplicado():
    # Arrange
    repositorio_mock = AsyncMock()
    usuario_existente = Usuario(
        id="123",
        nombre="Otro Usuario",
        email="paulo@example.com",
        password_hash="hash",
        rol=RolUsuario.OPERADOR,
        estado=True,
    )
    repositorio_mock.buscar_por_email.return_value = usuario_existente
    hasher_mock = MagicMock()

    caso_uso = CrearUsuarioUseCase(repository=repositorio_mock, hasher=hasher_mock)

    # Act & Assert
    with pytest.raises(ValueError, match="El email ya fue registrado"):
        await caso_uso.ejecutar(
            nombre="Paulo",
            email="paulo@example.com",
            password_hash="Pauloolivo",
            rol=RolUsuario.ADMIN,
        )

    # Si falla por duplicado, jamás debió intentar hashear ni guardar
    hasher_mock.hashear.assert_not_called()
    repositorio_mock.guardar.assert_not_awaited()
