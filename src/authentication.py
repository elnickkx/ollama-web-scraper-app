
# -*- coding: utf-8 -*-
"""

@Filename : authentication module
@created :  Dept 28 11:42 2020
@project: atlys-interview-assignment
@author : Nikkhil Butola
"""

from fastapi import Depends, HTTPException, status
from secure_handling import verify_password
from db import UserTable
import time
from functools import wraps
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
loggingFormat = "[%(filename)s: %(lineno)s- %(funcName)11s() ] %(asctime)s: %(name)s:%(levelname)s %(message)s"
logging.basicConfig(format=loggingFormat)


async def authenticate_user(email_addr: str, password: str):
    """

    :param email_addr:
    :param password:
    :return:
    """

    _user = await UserTable.get_user_by_email(email_addr=email_addr)
    if not _user:
        return False

    if not verify_password(password, _user.hashed_password):
        return False

    return _user


def perform_retry(max_retries: int , wait_time: int):
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

__all__ = ["authenticate_user", "verify_password"]