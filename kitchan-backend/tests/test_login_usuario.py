# Test del caso de uso de login: valida que se respete el hasheo de
# contraseñas ya existente y que el rol viaje correcto hacia el generador de token
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.kitchan.modules.usuarios.application.use_cases import LoginUsuarioUseCase
from src.kitchan.modules.usuarios.domain.entities import Usuario, RolUsuario


def _crear_usuario(rol):
    return Usuario(
        id="123",
        nombre="Isaac Puga",
        email="isaac.puga@udla.edu.ec",
        password_hash="hash_guardado",
        rol=rol,
        estado=True,
    )


@pytest.mark.anyio
@pytest.mark.parametrize("rol", [RolUsuario.ADMIN, RolUsuario.OPERADOR])
async def test_login_exitoso_por_rol(rol):
    # Arrange
    usuario = _crear_usuario(rol)
    repositorio_mock = AsyncMock()
    repositorio_mock.buscar_por_email.return_value = usuario

    hasher_mock = MagicMock()
    hasher_mock.verificar.return_value = True

    token_generator_mock = MagicMock()
    token_generator_mock.generar_token.return_value = "token-falso"

    caso_uso = LoginUsuarioUseCase(
        repository=repositorio_mock,
        hasher=hasher_mock,
        token_generator=token_generator_mock,
    )

    # Act
    usuario_resultado, token = await caso_uso.ejecutar(
        email="isaac.puga@udla.edu.ec", password="claveCorrecta123"
    )

    # Assert
    assert usuario_resultado == usuario
    assert token == "token-falso"
    hasher_mock.verificar.assert_called_once_with("claveCorrecta123", "hash_guardado")
    token_generator_mock.generar_token.assert_called_once_with(
        {"sub": usuario.email, "id": usuario.id, "rol": rol.value}
    )


@pytest.mark.anyio
async def test_login_credenciales_invalidas_password_incorrecto():
    # Arrange
    usuario = _crear_usuario(RolUsuario.ADMIN)
    repositorio_mock = AsyncMock()
    repositorio_mock.buscar_por_email.return_value = usuario

    hasher_mock = MagicMock()
    hasher_mock.verificar.return_value = False

    token_generator_mock = MagicMock()

    caso_uso = LoginUsuarioUseCase(
        repository=repositorio_mock,
        hasher=hasher_mock,
        token_generator=token_generator_mock,
    )

    # Act & Assert
    with pytest.raises(ValueError, match="Credenciales inválidas"):
        await caso_uso.ejecutar(
            email="isaac.puga@udla.edu.ec", password="claveIncorrecta"
        )

    token_generator_mock.generar_token.assert_not_called()


@pytest.mark.anyio
async def test_login_usuario_no_encontrado():
    # Arrange
    repositorio_mock = AsyncMock()
    repositorio_mock.buscar_por_email.return_value = None

    hasher_mock = MagicMock()
    token_generator_mock = MagicMock()

    caso_uso = LoginUsuarioUseCase(
        repository=repositorio_mock,
        hasher=hasher_mock,
        token_generator=token_generator_mock,
    )

    # Act & Assert
    with pytest.raises(ValueError, match="Credenciales inválidas"):
        await caso_uso.ejecutar(
            email="no.existe@udla.edu.ec", password="cualquierClave"
        )

    # Si el usuario no existe, ni se debe intentar verificar password ni generar token
    hasher_mock.verificar.assert_not_called()
    token_generator_mock.generar_token.assert_not_called()


@pytest.mark.anyio
async def test_login_rol_no_reconocido():
    # Arrange: simulamos un dato corrupto donde el rol no es un RolUsuario válido
    usuario = _crear_usuario(rol="GERENTE")
    repositorio_mock = AsyncMock()
    repositorio_mock.buscar_por_email.return_value = usuario

    hasher_mock = MagicMock()
    hasher_mock.verificar.return_value = True

    token_generator_mock = MagicMock()

    caso_uso = LoginUsuarioUseCase(
        repository=repositorio_mock,
        hasher=hasher_mock,
        token_generator=token_generator_mock,
    )

    # Act & Assert
    with pytest.raises(ValueError, match="Rol de usuario no reconocido"):
        await caso_uso.ejecutar(
            email="isaac.puga@udla.edu.ec", password="claveCorrecta123"
        )

    token_generator_mock.generar_token.assert_not_called()
