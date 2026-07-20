import pytest
from unittest.mock import AsyncMock
from src.kitchan.modules.usuarios.application.use_cases import CrearUsuarioUseCase
from src.kitchan.modules.usuarios.domain.entities import Usuario, RolUsuario


@pytest.mark.anyio
async def test_crear_usuario_exitoso():
    # Arrange (Preparar el escenario)
    repositorio_mock = AsyncMock()
    repositorio_mock.buscar_por_email.return_value = None
    
    async def side_effect(usuario: Usuario):
        return usuario
    repositorio_mock.guardar.side_effect = side_effect

    caso_uso = CrearUsuarioUseCase(repository=repositorio_mock)

    # Act (Ejecutar la acción)
    resultado = await caso_uso.ejecutar(
        nombre="Isaac Puga",
        email="isaac.puga@udla.edu.ec",
        password_hash="password_falsificado_hash",
        rol=RolUsuario.ADMIN
    )

    # Assert (Verificar el resultado)
    assert resultado is not None
    assert resultado.nombre == "Isaac Puga"
    assert resultado.email == "isaac.puga@udla.edu.ec"
    assert resultado.rol == RolUsuario.ADMIN
    assert resultado.estado is True
    
    repositorio_mock.buscar_por_email.assert_awaited_once_with("isaac.puga@udla.edu.ec")
    repositorio_mock.guardar.assert_awaited_once()


@pytest.mark.anyio
async def test_crear_usuario_email_duplicado():
    # Arrange
    repositorio_mock = AsyncMock()
    usuario_existente = Usuario(
        id="123",
        nombre="Otro Usuario",
        email="isaac.puga@udla.edu.ec",
        password_hash="hash",
        rol=RolUsuario.OPERADOR,
        estado=True
    )
    repositorio_mock.buscar_por_email.return_value = usuario_existente

    caso_uso = CrearUsuarioUseCase(repository=repositorio_mock)

    # Act & Assert
    with pytest.raises(ValueError, match="El email ya fue registrado"):
        await caso_uso.ejecutar(
            nombre="Isaac Puga",
            email="isaac.puga@udla.edu.ec",
            password_hash="password_falsificado_hash",
            rol=RolUsuario.ADMIN
        )

    repositorio_mock.guardar.assert_not_awaited()