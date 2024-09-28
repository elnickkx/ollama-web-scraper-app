

# -*- coding: utf-8 -*-
"""

@Filename : pydantic serializer
@created :  Dept 28 11:42 2020
@project: atlys-interview-assignment
@author : Nikkhil Butola
"""

import typing
from pydantic import BaseModel, field_validator, EmailStr, Field, validator
from datetime import timedelta, date, time, datetime


class UserLogin(BaseModel):
    name: str
    id: str
    email_addr: EmailStr = Field(default=None, max_length=254)


"""
create user -- update, delete, get
transaction -- create, update
booking -- create, update, delete, and allow admin to create events


Keyword arguments:
argument -- description
Return: return_description
"""


class UserData(BaseModel):
    username: typing.Optional[str]
    email_address: typing.Optional[str]
    first_name: typing.Optional[str]
    last_name: typing.Optional[str]
    is_admin: typing.Optional[bool] = False
    is_parent: bool = False

    class Config:
        from_attributes = True


class CreateUser(UserData):
    password: str

    class Config:
        from_attributes = True


class LoginData(BaseModel):
    username: typing.Optional[str]
    email: typing.Optional[str]
    password: str

    class Config:
        from_attributes = True


class CheckoutSession(BaseModel):
    session_id: str

    class Config:
        from_attributes = True


# the event will expire once the current-date > end_date >> cron.job
# multi-events can exist with same event_name >> the prev needs to set
# is_active to False
class CreateEvent(BaseModel):
    event_name: typing.Optional[str] = "scraping"
    website_uri: str
    start_date: datetime
    status: typing.Optional[str] = "OPENED"
    user_id: int
    pages: typing.Optional[int] = 3
    proxy_string: typing.Optional[str] = ""

    class Config:
        from_attributes = True


class EventScrapeData(BaseModel):
    event_id: str
    user_id: typing.Optional[int]
    website_uri: typing.Union[str, typing.List]
    page_limiter: int
    # starts_at: typing.Optional[str] = "0" # time-str --> 1330

    class Config:
        from_attributes = True
        validate_assignment = True

    @field_validator("page_limiter")
    def set_page_limiter(cls, page_limiter):
        return page_limiter or 1


__all__ = ["UserLogin", "UserData", "CreateUser", "LoginData", "CheckoutSession", "EventSeatData", "CreateEvent",
           "EventMetadata", "EventBookinData", "EventScrapeData"]
