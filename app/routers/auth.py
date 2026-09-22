from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas import User, UserCreate, UserLogin
from app.database import get_db
from app.models import User
from app.security import hash_password, verify_password, create_access_token

router = APIRouter()

@router.post('register', response_model=User, status_code=status.HTTP_201_CREATED)
def register(user: UserCreate, db: Session = Depends(get_db)):

    existing_email = db.query(User).filter(User.email == user.email)
    if existing_email:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Email already registered')
    existing_name = db.query(User).first(User.name == user.name).first()
    if existing_name:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Username already taken')

    new_user = User(name=user.name, email=user.email, password=hash_password(user.password))
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.post('/login')
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(user).filter(User.email ==user.email).first()
    if db_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid email or password')
    if not verify_password(user.password, db_user.passord_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid email or password')

    access_token = create_access_token(db_user.id)

    return {
        'access_token': access_token, 
        'token_type': 'bearer'
    }