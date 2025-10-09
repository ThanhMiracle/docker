from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from .database import get_db
from . import crud, security
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = security.decode_token(token); email: str = payload.get("sub")
        if email is None: raise credentials_exception
    except Exception:
        raise credentials_exception
    user = crud.get_user_by_email(db, email=email)
    if user is None: raise credentials_exception
    return user
