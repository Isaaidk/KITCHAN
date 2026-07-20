#CASO DE USO 
#Define que los datos cumplan con el caso de uso, en este caso debe de revisar primero que el email no este creado 
#y si no lo esta pide que se almacene el usuario y tma todos los datos 
from src.kitchan.modules.usuarios.domain.entities import Usuario, RolUsuario
from src.kitchan.modules.usuarios.application.ports import IUsuarioRepository
import uuid

class CrearUsuarioUseCase:
    def __init__(self,repository:IUsuarioRepository):
        self.repository = repository

    async def ejecutar(self, nombre: str, email: str, password_hash: str, rol: RolUsuario) -> Usuario:
        # Validar si el usuario existe 
        usuario_existente = await self.repository.buscar_por_email(email)
        if usuario_existente:
            raise ValueError("El email ya fue registrado")
        
        # Creacion de un Usuario con los datos correctos
        nuevoUsuario = Usuario(
            id=str(uuid.uuid4()),
            nombre=nombre,          # Pasamos la variable local
            email=email,            # Pasamos la variable local
            password_hash=password_hash, # Pasamos la variable local
            rol=rol,                # Pasamos la variable local
            estado=True             # Asignación directa del valor por defecto
        )

        return await self.repository.guardar(nuevoUsuario)

