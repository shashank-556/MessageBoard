# Message Board
This is the backend for a real time group chat web app using **fastapi** and **websockets**. The api uses **mongodb** for persistent storage of messages. The backend uses **OAuth2** with **JWT** tokens for authorization.

## Installation

Create a python virtual environment then proceed with installation.

```
# clone the repo
$ git clone https://github.com/shashank-556/MessageBoard.git

# change the working directory to MessageBoard
$ cd MessageBoard

# install the requirements
$ python3 -m pip install -r requirements.txt
```

## Setup

Create a json file with the name *secrets.json* to store the secret that will be used to sign JWT tokens. The *secrets.json* file 

```json
{"SECRET_KEY":""}
```
You can create a secure random secret key in bash using the following command 
```bash
openssl rand -hex 32
```

## Documentation 

FastAPI generates documentation on its own which you can find on `base_url/docs` or `base_url/redoc`