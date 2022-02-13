from string import ascii_letters
from fastapi import FastAPI
from random import randint
from fastapi.security import OAuth2PasswordBearer
from schemas import baseUserModel
import pymongo

app = FastAPI()

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

async def generate_username(name:str):
    while(True) :
        num = randint(1,4)
        temp = f"{name}{randint(1,99999)}"
        if user_coll.find_one({'username':temp}) is None :
            return temp


@app.post('/api/user/register')
async def register_users(user: baseUserModel):
    user.username = await generate_username(user.name)
    user.created_room,user.joined_room = [],[]
    user_coll.insert_one(user.dict())
    return user
            