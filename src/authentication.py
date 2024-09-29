# -*- coding: utf-8 -*-
"""

@Filename : authentication module
@created :  Sept 28 11:42 2020
@project: atlys-interview-assignment
@author : Nikkhil Butola
"""
import traceback
import typing

import jwt
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer
from secure_handling import verify_password, _gen_oauth2_bearer
from db import UserTable
import time
from functools import wraps
import logging
from config import SECRET_KEY, ALGORITHM
from pydantic_serializer import CreateUser

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
loggingFormat = "[%(filename)s: %(lineno)s- %(funcName)11s() ] %(asctime)s: %(name)s:%(levelname)s %(message)s"
logging.basicConfig(format=loggingFormat)


async def authenticate_user(*, email_addr: str, password: str = None):
    """

    :param email_addr:
    :param password:
    :return:
    """

    _user = await UserTable.get_user_by_email(email_addr=email_addr)
    if not _user:
        return False

    if password and not verify_password(password, _user.hashed_password):
        return False

    return _user


class AsyncJWTBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super(AsyncJWTBearer, self).__init__(auto_error=auto_error)

    async def __call__(self, request: Request):
        """
        re-constructing the Base HTTPBearer __call__ method definition
        for misleading `authorization` via postman requests
        """
        __credentials = await super(AsyncJWTBearer, self).__call__(request)
        if not __credentials:
            from fastapi.security.utils import get_authorization_scheme_param

            authorization = request.headers.get("authorization")
            scheme, __credentials = get_authorization_scheme_param(authorization)

            if not (authorization and scheme and __credentials):
                if self.auto_error:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN, detail="Invalid authentication credentials ..."
                    )

                else:
                    return None

            if scheme.lower() != "bearer":
                if self.auto_error:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Invalid authentication scheme ...",
                    )

                else:
                    return None

        ## verify the credentials, decode the JWT [`bcrypt`] token
        if not isinstance(__credentials, str):
            __credentials = __credentials.credentials

        try:
            __is_validated, __user_id = await self.authenticate_current_user(jwt_token=__credentials)
            if not __is_validated:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token or expired token ...")

            else:
                request.cookies.update(
                    **{
                        "user_id": str(__user_id),
                    }
                )

        except Exception:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid authentication token ...",
            )

        else:
            return __credentials

    async def authenticate_current_user(self, *, jwt_token: typing.Annotated[str, Depends(_gen_oauth2_bearer)]):
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

        try:
            __payload_decode = jwt.decode(jwt_token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = __payload_decode.get('username')
            email: str = __payload_decode.get("sub")

            if not username and not email:
                raise credentials_exception

            if _is_valid_user := await authenticate_user(email_addr=email):
                return _is_valid_user, __payload_decode.get('user_id')

            else:
                raise credentials_exception

        except jwt.InvalidTokenError:
            logger.error(traceback.format_exc())
            raise jwt.InvalidTokenError

    @classmethod
    async def get_current_active_user(
            cls, *, current_user: typing.Annotated[CreateUser, Depends(authenticate_current_user)]
    ):
        if not current_user.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user ...")

        return current_user


def perform_retry(max_retries: int, wait_time: int):
    """

    :param max_retries: number of maximum retries before exist
    :param wait_time: waitin' timelapse in seconds
    :return:
    """

    def _retry_handling(func):
        """

        :param func:
        :return:
        """

        @wraps(func)
        def _wrapper(*args, **kwargs):
            """

            :param args:
            :param kwargs:
            :return:
            """

            retries = 0
            if retries < max_retries:
                try:
                    result = func(*args, **kwargs)
                    return result

                except Exception as e:
                    logger.error(traceback.format_exc())
                    retries += 1
                    time.sleep(wait_time)

            else:
                raise Exception(f"Max retries of function {func} exceeded")

        return _wrapper

    return _retry_handling


"""
example for marking-up the usage
@perform_retry(max_retries=5, wait_time=1)
def example_function():
    # function that may raise an exception
    pass

"""

__all__ = ["authenticate_user", "verify_password", "AsyncJWTBearer"]
