import json
from fastapi import Depends, FastAPI , HTTPException
from random import randint
from fastapi.security import OAuth2PasswordBearer,OAuth2PasswordRequestForm
from schemas import User_in,baseUserModel
import pymongo

app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='token')

def get_secret_key():
    with open('secrets.json','r') as fh :
        js = json.load(fh)
        return js['SECRET_KEY']
SECRET_KEY = get_secret_key()

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

async def fake_password_hash(password):
    pass

async def decode_token(token):
    return {}

async def get_current_user(token: str = Depends(oauth2_scheme)):
    user = await decode_token(token)
    return user

async def generate_username(name:str):
    while(True) :
        num = randint(1,4)
        temp = f"{''.join(name.split())}{randint(1,99999)}"
        if user_coll.find_one({'username':temp}) is None :
            return temp

# ------------------------------------------------------------------------------

@app.post('/user/register',response_model=baseUserModel,response_model_exclude=['password'],status_code=201)
async def register_users(user: User_in):
    user = baseUserModel(**user.dict())
    user.username = await generate_username(user.name)
    user_coll.insert_one(user.dict())
    return user

@app.post('/token')
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = user_coll.find_one({'username':form_data.username})
    if not user:
        raise HTTPException(status_code=400,detail='Given username does not exist')
    
    hash_password = fake_password_hash(form_data.password)
    if not hash_password == user.password :
        raise HTTPException(status_code=400,detail='Given password is incorrect')
    
    return {'Access_token':user.username}


@app.get('/user',response_model=baseUserModel,response_model_exclude=['password'])
async def user_profile(user: baseUserModel = Depends(get_current_user)) :
    return user