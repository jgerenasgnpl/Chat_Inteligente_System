from typing import Generator
from fastapi import Depends, HTTPException, status, Security
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app import crud, models, schemas

# 1. Define de dónde sale el token
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/token",
    scopes={"read": "Leer datos", "write": "Escribir datos"}
)

# 2. Sesión de BD
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 3. Verificar y decodificar JWT
def _decode_token(token: str, credentials_exception):
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        token_data = schemas.TokenPayload(sub=user_id, scopes=payload.get("scopes", []))
    except JWTError:
        raise credentials_exception
    return token_data

# 4. Obtener usuario actual
def get_current_user(
    security_scopes: SecurityScopes,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar las credenciales",
        headers={"WWW-Authenticate": f'Bearer scope="{security_scopes.scope_str}"'},
    )
    token_data = _decode_token(token, credentials_exception)

    # Comprueba scopes si los declaraste en el endpoint
    for scope in security_scopes.scopes:
        if scope not in token_data.scopes:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No tiene permisos suficientes",
                headers={"WWW-Authenticate": f'Bearer scope="{security_scopes.scope_str}"'},
            )

    user = crud.user.get(db, id=int(token_data.sub))
    if not user:
        raise credentials_exception
    return user

def get_current_active_user(
    current_user: models.User = Security(get_current_user, scopes=["read"])
) -> models.User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Usuario inactivo")
    return current_user

# 5. Dependencia de admin (opcional)
def get_current_active_admin(
    current_user: models.User = Security(get_current_user, scopes=["write"])
) -> models.User:
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="No autorizado")
    return current_user