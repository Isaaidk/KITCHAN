from unittest.mock import AsyncMock, MagicMock

import pytest
from src.kitchan.modules.usuarios.application.use_cases import (
    EditarUsuarioUCase, ListarUsuariosUCase)
from src.kitchan.modules.usuarios.domain.entities import RolUsuario, Usuario


@pytest.mark.anyio
async def test_editar_contrasena_exitoso():
    # Arrange
    repositorio_mock = AsyncMock()
    hasher_mock = MagicMock()

    usuario = Usuario(
        id="123",
        restaurante_id="db3dfd6b-c78d-4306-81e3-81078c521c95",
        nombre="Isaac",
        email="isaac.puga@udla.edu.ec",
        password_hash="hash_viejo",
        rol=RolUsuario.ADMIN,
        estado=True,
    )

    repositorio_mock.buscar_por_email.return_value = usuario
    repositorio_mock.editar_contraseña.return_value = None
    hasher_mock.hashear.return_value = "nuevo_hash_super_seguro"

    caso_uso = EditarUsuarioUCase(repository=repositorio_mock, hasher=hasher_mock)

    # Act
    await caso_uso.ejecutar(
        email="isaac.puga@udla.edu.ec",
        password_hash="NuevaClave123",
    )

    # Assert
    repositorio_mock.buscar_por_email.assert_awaited_once_with("isaac.puga@udla.edu.ec")
    hasher_mock.hashear.assert_called_once_with("NuevaClave123")
    repositorio_mock.editar_contraseña.assert_awaited_once_with(
        "isaac.puga@udla.edu.ec",
        "nuevo_hash_super_seguro",  # Aseguramos que guarde el hash, no el texto plano
    )


@pytest.mark.anyio
async def test_editar_contrasena_usuario_no_existe():
    # Arrange
    repositorio_mock = AsyncMock()
    repositorio_mock.buscar_por_email.return_value = None
    hasher_mock = MagicMock()

    caso_uso = EditarUsuarioUCase(repository=repositorio_mock, hasher=hasher_mock)

    # Act & Assert
    with pytest.raises(ValueError, match="El usuario no existe"):
        await caso_uso.ejecutar(
            email="isaac.puga@udla.edu.ec",
            password_hash="NuevaClave123",
        )

    # Verificamos que si no existe, no procese nada extra
    hasher_mock.hashear.assert_not_called()
    repositorio_mock.editar_contraseña.assert_not_awaited()


# ----- Pruebas para Listar (Este caso de uso usualmente no requiere el hasher) -----


@pytest.mark.anyio
async def test_listar_usuarios():
    # Arrange
    repositorio_mock = AsyncMock()
    usuarios = [
        Usuario(
            id="1",
            restaurante_id="db3dfd6b-c78d-4306-81e3-81078c521c95",
            nombre="Isaac",
            email="isaac@udla.edu.ec",
            password_hash="123",
            rol=RolUsuario.ADMIN,
            estado=True,
        ),
        Usuario(
            id="2",
            restaurante_id="db3dfd6b-c78d-4306-81e3-81078c521c95",
            nombre="Santiago",
            email="santiago@udla.edu.ec",
            password_hash="456",
            rol=RolUsuario.OPERADOR,
            estado=True,
        ),
    ]
    repositorio_mock.listar.return_value = usuarios

    # Asumimos que ListarUsuariosUCase solo requiere el repositorio
    caso_uso = ListarUsuariosUCase(repository=repositorio_mock)

    # Act
    resultado = await caso_uso.ejecutar()

    # Assert
    assert len(resultado) == 2
    assert resultado[0].nombre == "Isaac"
    assert resultado[1].nombre == "Santiago"
    repositorio_mock.listar.assert_awaited_once()


@pytest.mark.anyio
async def test_listar_usuarios_vacio():
    # Arrange
    repositorio_mock = AsyncMock()
    repositorio_mock.listar.return_value = []

    caso_uso = ListarUsuariosUCase(repository=repositorio_mock)

    # Act
    resultado = await caso_uso.ejecutar()

    # Assert
    assert resultado == []
    repositorio_mock.listar.assert_awaited_once()
