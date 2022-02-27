from datetime import datetime, timedelta
import json
from fastapi import Depends, FastAPI , HTTPException, WebSocket,WebSocketDisconnect,Request
import random
import string
from typing import List
from fastapi.security import OAuth2PasswordBearer,OAuth2PasswordRequestForm
from passlib.context import CryptContext
from jose import jwt,JWTError
from starlette.websockets import WebSocketState
from schemas import User_in,baseUserModel,Token,roomModel_in,roomModel_out,join_with_code,messageModel
import pymongo

app = FastAPI()

class CustomOAuth2PasswordBearer(OAuth2PasswordBearer):
    async def __call__(self, request: Request = None, websocket: WebSocket = None):
        return await super().__call__(request or websocket)


oauth2_scheme = CustomOAuth2PasswordBearer(tokenUrl="login")
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

async def current_user(token: str) :
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


async def get_current_user(token: str = Depends(oauth2_scheme)):
    return await current_user(token)

def check_if_key_values_exist(coll: pymongo.collection.Collection,di:dict):
    data = coll.find_one(di)
    if data is None :
        return False
    return True

def get_chatroom(code_in:join_with_code) :
    room = chatroom_coll.find_one({'code':code_in.code})
    if room is None :
        raise HTTPException(status_code=404,detail='No chatroom with given code exists')
    return room

def generate_username(name:str):
    while(True) :
        username = f"{''.join(name.split())}{random.randint(1,99999)}"
        if not check_if_key_values_exist(user_coll,{'username':username}) :
            return username

def generate_chatroom_code():
    while(True):
        num = random.randint(6,8)
        code = ''.join(random.choices(string.ascii_lowercase,k=num))
        if not check_if_key_values_exist(chatroom_coll,{'code':code}) :
            return code

# ------------------------------------------------------------------------------

@app.post('/user/register',response_model=baseUserModel,response_model_exclude=['password'],status_code=201)
async def register_users(user_in: User_in):
    user = baseUserModel(**user_in.dict())
    user.username= generate_username(user.name)
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
async def user_profile(user = Depends(get_current_user)) :
    return user

@app.post('/room',response_model=roomModel_out,status_code=201)
async def create_chat_room(room: roomModel_in,user = Depends(get_current_user)):
    chatroom = roomModel_out(**room.dict(),code=generate_chatroom_code(),creater=user['username'])
    chatroom_coll.insert_one(chatroom.dict())
    user['created_room'].append(chatroom.code)
    user_coll.replace_one({'_id':user['_id']},user)
    return chatroom

@app.post('/room/join',response_model=roomModel_out)
async def join_chat_room(room = Depends(get_chatroom),user = Depends(get_current_user)) :
    # return 200 if already a member
    if user['username'] in room['members'] :
        return room

    # return 403 if creater tries to join his own room
    if user['username'] == room['creater'] :
        raise HTTPException(status_code=403,detail='Not allowed')

    room['members'].append(user['username'])
    user['joined_room'].append(room['code'])
    chatroom_coll.replace_one({'_id':room['_id']},room)
    user_coll.replace_one({'_id':user['_id']},user)
    return room

# ----------------------------------------------------------------------------------------------

class ConnectionManager() :

    def __init__(self) -> None:
        self.active_connections: dict[str,dict[str,WebSocket]] = {}
    
    async def connect(self,websocket:WebSocket,room_code,username) :
        await websocket.accept()
        if room_code in self.active_connections :
            self.active_connections[room_code][username] = websocket
        else :
            self.active_connections[room_code] = {username:websocket}
        print(self.active_connections)

    def disconnect(self,room_code,username) :
        self.active_connections[room_code].pop(username).close()
        print(self.active_connections)
    
    async def broadcast(self,msg:messageModel) :
        for k in self.active_connections[msg.code] :
            await self.active_connections[msg.code][k].send_json(msg.json())

manager = ConnectionManager()

@app.websocket('/room/{room_code}/ws')    
async def chat_room_websocket(websocket: WebSocket,room_code:str):
    
    try :
        room =  get_chatroom(join_with_code(code=room_code))
        tok = await oauth2_scheme(websocket=websocket)
        user = await current_user(tok)
    except HTTPException :
        await websocket.close(code = 1008)

    if websocket.application_state == WebSocketState.CONNECTING :
        await manager.connect(room_code=room_code,username=user["username"],websocket=websocket)
        await websocket.send_json(room["msgs"])
        try:
            while True:
                data = await websocket.receive_text()
                msg = messageModel(message=data,code=room_code,writer=user["username"],created_at=datetime.now())
                room["msgs"].append(msg.json())
                chatroom_coll.replace_one({'_id':room['_id']},room)
                await manager.broadcast(msg)
        except WebSocketDisconnect:
            manager.disconnect(room_code,user["username"])

    