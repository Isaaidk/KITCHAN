import pytest
from unittest.mock import AsyncMock
from src.kitchan.modules.usuarios.application.use_cases import EliminarUsuarioUseCase
from src.kitchan.modules.usuarios.domain.entities import Usuario, RolUsuario


@pytest.mark.anyio
async def test_eliminar_usuario_exitoso():
    # Arrange (Preparar el escenario)
    usuario_existente = Usuario(
        id="123",
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
    await caso_uso.ejecutar(usuario_id="123")

    # Assert (Verificar el resultado)
    repositorio_mock.buscar_por_id.assert_awaited_once_with("123")
    repositorio_mock.eliminar.assert_awaited_once_with("123")


@pytest.mark.anyio
async def test_eliminar_usuario_no_encontrado():
    # Arrange
    repositorio_mock = AsyncMock()
    repositorio_mock.buscar_por_id.return_value = None

    caso_uso = EliminarUsuarioUseCase(repository=repositorio_mock)

    # Act & Assert
    with pytest.raises(ValueError, match="Usuario no encontrado"):
        await caso_uso.ejecutar(usuario_id="id-inexistente")

    repositorio_mock.eliminar.assert_not_awaited()
