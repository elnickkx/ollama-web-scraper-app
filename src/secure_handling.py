
# -*- coding: utf-8 -*-
"""

@Filename : secure handling
@created :  Dept 28 11:42 2020
@project: atlys-interview-assignment
@author : Nikkhil Butola
"""

import jwt
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from datetime import datetime, timedelta
from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
import logging

_gen_oauth2_bearer = OAuth2PasswordBearer(tokenUrl="/api/token")
pwd_crypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
loggingFormat = "[%(filename)s: %(lineno)s- %(funcName)11s() ] %(asctime)s: %(name)s:%(levelname)s %(message)s"
logging.basicConfig(format=loggingFormat)


def get_password_hash(_password: str) -> str:
    """

    :param _password:
    :return:
    """
    return pwd_crypt_context.hash(_password)


def verify_password(input_password: str, hashed_password: str) -> bool:
    """

    :param input_password:
    :param hashed_password:
    :return:
    """
    return pwd_crypt_context.verify(input_password, hashed_password)


def create_access_token(*, data: dict, expires_delta: timedelta = None):
    """

    :param data:
    :param expires_delta:
    :return:
    """
    _encoder_data = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(seconds=1800)

    _encoder_data.update({"exp": expire})
    encoded_jwt_repr = jwt.encode(_encoder_data, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt_repr