from unittest.mock import AsyncMock

import pytest

from src.kitchan.modules.usuarios.application.use_cases import EliminarUsuarioUseCase
from src.kitchan.modules.usuarios.domain.entities import RolUsuario, Usuario


@pytest.mark.anyio
async def test_eliminar_usuario_exitoso():
    # Arrange (Preparar el escenario)
    usuario_existente = Usuario(
        id="123",
        restaurante_id="db3dfd6b-c78d-4306-81e3-81078c521c95",
        nombre="Isaac Puga",
        email="isaac.puga@udla.edu.ec",
        password_hash="hash",
        rol=RolUsuario.ADMIN,
        estado=True,
    )
    repositorio_mock = AsyncMock()
    repositorio_mock.buscar_por_id.return_value = usuario_existente

    caso_uso = EliminarUsuarioUseCase(repository=repositorio_mock)

    # Act (Ejecutar la acción)
    await caso_uso.ejecutar(
        usuario_id="123", admin_restaurante_id="db3dfd6b-c78d-4306-81e3-81078c521c95"
    )

    # Assert (Verificar el resultado)
    repositorio_mock.buscar_por_id.assert_awaited_once_with("123")
    repositorio_mock.eliminar.assert_awaited_once_with("123")


@pytest.mark.anyio
async def test_eliminar_usuario_de_otro_restaurante_rechazado():
    # Multi-tenant: un admin no puede eliminar un usuario de OTRO restaurante,
    # aunque conozca su id.
    usuario_de_otro_restaurante = Usuario(
        id="123",
        restaurante_id="restaurante-A",
        nombre="Isaac Puga",
        email="isaac.puga@udla.edu.ec",
        password_hash="hash",
        rol=RolUsuario.ADMIN,
        estado=True,
    )
    repositorio_mock = AsyncMock()
    repositorio_mock.buscar_por_id.return_value = usuario_de_otro_restaurante

    caso_uso = EliminarUsuarioUseCase(repository=repositorio_mock)

    with pytest.raises(ValueError, match="Usuario no encontrado"):
        await caso_uso.ejecutar(usuario_id="123", admin_restaurante_id="restaurante-B")

    repositorio_mock.eliminar.assert_not_awaited()


@pytest.mark.anyio
async def test_eliminar_usuario_no_encontrado():
    # Arrange
    repositorio_mock = AsyncMock()
    repositorio_mock.buscar_por_id.return_value = None

    caso_uso = EliminarUsuarioUseCase(repository=repositorio_mock)

    # Act & Assert
    with pytest.raises(ValueError, match="Usuario no encontrado"):
        await caso_uso.ejecutar(
            usuario_id="id-inexistente", admin_restaurante_id="cualquier-restaurante"
        )

    repositorio_mock.eliminar.assert_not_awaited()
