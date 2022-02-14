from datetime import datetime
from pydantic import BaseModel,Field
from typing import List

class User_in(BaseModel) :
    name: str = Field(title="Full name of the user",max_length=30)
    password: str

class baseUserModel(User_in) :
    username: str = Field(None,title='Unique user name for user',max_length=40)
    created_room: List[str] = Field([])
    joined_room: List[str] = Field([])

class roomModel_in(BaseModel) :
    name: str = Field(title='Name of the chat room',max_length=30)

class roomModel_out(roomModel_in) :
    code:str = Field(title="Unique code of the chatroom",max_length=8)
    msgs: List[dict] = Field([],title="All the messages in the chat room")

class messageModel(BaseModel) :
    msg: str = Field(title='Message sent by a user',max_length=300)
    writer: str
    created_at: datetime