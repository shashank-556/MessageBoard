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

class join_with_code(BaseModel) :
    code:str = Field(title="Chatroom Code",description="Unique code to join the chatroom",max_length=8)

class roomModel_out(roomModel_in) :
    code:str = Field(title="Chatroom Code",description="Unique code to join the chatroom",max_length=8)
    creater: str = Field(max_length=40)
    members: List[str] = Field([])

class messageModel(BaseModel) :
    message: str = Field(title='The message',max_length=300)
    code: str = Field(max_length=8)
    writer: str = Field(title = 'Username',description='Username of the user who wrote sent the message')
    created_at: datetime = Field(None)

class Token(BaseModel):
    access_token: str
    token_type: str