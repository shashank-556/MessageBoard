from datetime import datetime, timedelta
import json
from fastapi import Depends, FastAPI , HTTPException
from random import randint
from fastapi.security import OAuth2PasswordBearer,OAuth2PasswordRequestForm
from passlib.context import CryptContext
from jose import jwt,JWTError
from schemas import User_in,baseUserModel,Token
import pymongo

app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='token')
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_secret_key():
    with open('secrets.json','r') as fh :
        js = json.load(fh)
        return js['SECRET_KEY']
SECRET_KEY = get_secret_key()
ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_DAYS=30

# --------------------------------------------------------------------------------------------------

@app.on_event('startup')
async def startup_envents():
    database_url = 'mongodb://localhost:27017/'
    global mcl,mydb,user_coll,chatroom_coll
    mcl = pymongo.MongoClient(database_url)
    mydb = mcl['Messageboard']
    user_coll = mydb['Users']
    chatroom_coll = mydb['Rooms']

@app.on_event('shutdown')
async def shutdown_event():
    mcl.close()

# -----------------------------------------------------------------------------------------------------------------------------
async def verify_password(plain_pass,hash_pass):
    return pwd_context.verify(plain_pass,hash_pass)

async def get_password_hash(password):
    return pwd_context.hash(password)


async def create_access_token(data: dict,expire_delta: timedelta = None):
    to_encode = data.copy()

    if expire_delta:
        expire = datetime.utcnow()+ expire_delta
    else :
        expire = datetime.utcnow()+ timedelta(minutes=59)

    to_encode.update({"exp":expire})
    encoded_jwt = jwt.encode(to_encode,SECRET_KEY,algorithm=ALGORITHM)
    return encoded_jwt

async def authenticate_user(username: str, password: str):
    user = user_coll.find_one({'username':username})
    if not user:
        return False
    if not await verify_password(password, user['password']):
        return False
    return user


async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = user_coll.find_one({'username':username})
    if user is None:
        raise credentials_exception
    return user

async def generate_username(name:str):
    while(True) :
        num = randint(1,4)
        temp = f"{''.join(name.split())}{randint(1,99999)}"
        if user_coll.find_one({'username':temp}) is None :
            return temp

# ------------------------------------------------------------------------------

@app.post('/user/register',response_model=baseUserModel,response_model_exclude=['password'],status_code=201)
async def register_users(user_in: User_in):
    user = baseUserModel(**user_in.dict())
    user.username = await generate_username(user.name)
    user.password = await get_password_hash(user.password)
    user_coll.insert_one(user.dict())
    return user

@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    access_token = await create_access_token(data={"sub": user['username']}, expire_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}


@app.get('/user',response_model=baseUserModel,response_model_exclude=['password'])
async def user_profile(user: baseUserModel = Depends(get_current_user)) :
    return user