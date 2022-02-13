from datetime import datetime
from pydantic import BaseModel,Field
from typing import List

class baseUserModel(BaseModel) :
    name: str = Field(title="Full name of the user",max_length=30)
    username: str = Field(None,title='Unique user name for user',max_length=40)
    password: str
    created_room: List[str] = Field([])
    joined_room: List[str] = Field([])

class messageModel(BaseModel) :
    msg: str = Field(title='Message sent by a user',max_length=300)
    writer: str
    created_at: datetime