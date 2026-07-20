#Puerto de salida 
#Es el que define comunicacion entre el nucleo y el adaptador de salida 

from abc import ABC, abstractmethod
from typing import Optional
from src.kitchan.modules.usuarios.domain.entities import Usuario

class IUsuarioRepository(ABC):
    """
    Puerto de Salida: Define cómo el núcleo se comunica con la persistencia.
    """

    @abstractmethod
    async def guardar(self, usuario:Usuario) -> Usuario:
        pass

    @abstractmethod
    async def buscar_por_email(self, email:str) ->Optional[Usuario]:
        pass
