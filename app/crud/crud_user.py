from sqlalchemy.orm import Session
from typing import Optional

from app.models.user import User # Asegúrate de que este import sea correcto
from app.schemas.user import UserCreate # Asegúrate de que este import sea correcto

# Clase base para operaciones CRUD (opcional, pero útil para reutilizar código)
# class CRUDBase:
#     def __init__(self, model):
#         """
#         CRUD object with default methods to Create, Read, Update, Delete.
#         Args:
#             model: A SQLAlchemy model class
#         """
#         self.model = model

#     def get(self, db: Session, id: any) -> Optional[any]:
#         return db.query(self.model).filter(self.model.id == id).first()

#     # ... otros métodos genéricos ...

# Implementación específica para el modelo User
class CRUDUser:
    def get_by_wa_id(self, db: Session, *, wa_id: str) -> Optional[User]:
        """
        Obtiene un usuario por su ID de WhatsApp (wa_id).
        Args:
            db: Sesión de base de datos.
            wa_id: ID de WhatsApp del usuario.
        Returns:
            El objeto User si existe, None en caso contrario.
        """
        return db.query(User).filter(User.wa_id == wa_id).first()

    def create(self, db: Session, *, obj_in: UserCreate) -> User:
        """
        Crea un nuevo usuario.
        Args:
            db: Sesión de base de datos.
            obj_in: Objeto Pydantic con los datos para crear el usuario.
        Returns:
            El objeto User creado.
        """
        db_obj = User(
            wa_id=obj_in.wa_id,
            name=obj_in.name # Asumiendo que UserCreate tiene 'name'
            # Puedes añadir otros campos aquí si tu modelo User los tiene
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj) # Para obtener el ID autogenerado y otros defaults
        return db_obj

    # Podrías añadir métodos para actualizar o eliminar usuarios si son necesarios

# Instancia para ser usada en dependencias u otros módulos
user = CRUDUser()