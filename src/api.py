
# -*- coding: utf-8 -*-
"""

@Filename : fastapi server
@created :  Sept 28 11:42 2020
@project: atlys-interview-assignment
@author : Nikkhil Butola
"""
import sys
import typing
from time import perf_counter
import uvicorn
from pydantic import BaseModel, validator
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.routing import APIRouter
from db import *
from datetime import timedelta, date, time
from secure_handling import create_access_token
from fastapi import status as api_status
from authentication import authenticate_user, AsyncJWTBearer
import config
from collections import OrderedDict
from pydantic_serializer import (
    CreateUser,
    LoginData,
    UserData,
    CreateEvent,
    EventMetadata,
    EventScrapeData,

)
from scrape_query import perform_scraping_handling, check_scrape_event_exists
from redis_utility import aio_read_file_data, instream_json_parser


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
loggingFormat = "[%(filename)s: %(lineno)s- %(funcName)11s() ] %(asctime)s: %(name)s:%(levelname)s %(message)s"
logging.basicConfig(format=loggingFormat)


app = FastAPI(
    title="Event Management System", openapi_url="/fastapi", docs_url="/api/v1/docs", redoc_url="/fastapi/redoc"
)
main_router = APIRouter(prefix="/api/v1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@main_router.post("/create_user")
async def create_user(
        request: Request,
        params: CreateUser
):
    logger.info(f"user params {params} ...")
    _jwt_bearer: str = ""

    try:
        permissions: str
        if params:
            _user = await UserTable.create(params=params)
            if not _user:
                raise HTTPException(
                    status_code=api_status.HTTP_409_CONFLICT,
                    detail="Email address doesn't exists ...",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            try:
                access_token_expiry = timedelta(
                    minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES
                )

                # manage the login user permission
                if _user.is_admin:
                    permissions = "administrator"

                else:
                    permissions = "user"

                _user_meta = {
                    "user_id": str(_user.user_id),
                    "sub": _user.email,
                    "username": _user.username,
                    "is_active": _user.is_active,
                    "permissions": permissions
                }
                _jwt_bearer = create_access_token(data=_user_meta, expires_delta=access_token_expiry)

            except Exception:
                raise Exception

    except Exception as err:
        logger.error(traceback.format_exc())
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"error": err})

    else:
        return JSONResponse(status_code=status.HTTP_200_OK, content=dict(
                message=f"Successfully created admin user for {_user.email} ..."
                if params.is_admin else f"Successfully created login user for {_user.email} ...",
                access_token=_jwt_bearer,
                token_type="bearer"
            )
        )


@main_router.post("/login_user")
async def login_user(
        request: Request,
        params: LoginData
):
    logger.info(f"user { params = } ...")
    _jwt_bearer: str = ""

    try:
        permissions: str
        if params:
            _user = await authenticate_user(email_addr=params.email, password=params.password)
            if not _user:
                raise HTTPException(
                    status_code=api_status.HTTP_409_CONFLICT,
                    detail="Email address doesn't exists ...",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            try:
                access_token_expiry = timedelta(
                    minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES
                )

                # manage the login user permission
                if _user.is_admin:
                    permissions = "administrator"

                else:
                    permissions = "user"

                _user_meta = {
                    "user_id": str(_user.user_id),
                    "sub": _user.email,
                    "username": _user.username,
                    "is_active": _user.is_active,
                    "permissions": permissions
                }
                _jwt_bearer = create_access_token(data=_user_meta, expires_delta=access_token_expiry)

            except Exception:
                raise Exception

    except Exception as err:
        logger.error(traceback.format_exc())
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": err.__dict__})

    else:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=dict(
                token_type="bearer",
                message=f"Successfully created JWT token for login user: {_user.email} ... ",
                user_id=str(_user.user_id),
                access_token=_jwt_bearer,
            )
        )


@main_router.get("/update_user/{user_id}", dependencies=[Depends(AsyncJWTBearer())], response_model=None)
async def update_user(
        user_id,
        request: Request,
        params: UserData
):
    logger.info(f"user params {params} for {user_id}")

    try:
        if params:
            response = await UserTable.update_metadata(user_id=user_id, kwargs=params)
            if response in ["no user found"]:
                return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "User not found"})

    except Exception:
        logger.error(traceback.format_exc())
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "Format not found"})

    else:
        return JSONResponse(status_code=status.HTTP_200_OK, content={"msg": "Successfully updated user ..."})


@main_router.get("/get_event_status", dependencies=[Depends(AsyncJWTBearer())], response_model=None)
async def get_event_status():
    logger.info("fetching the possible event status values ...")
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": [
                "OPENED",
                "SCRAPED",
                "ERROR",
                "CANCELED",
                "CLOSED",
            ]
        }
    )


@main_router.post("/scrape/uri", dependencies=[Depends(AsyncJWTBearer())],  response_model=None, response_model_exclude_none=True)
async def initiate_scrape_event(
        request: Request,
        params: CreateEvent
) -> JSONResponse:
    # try:
    #     if _authorization := request.headers and request.headers.get("authorization", None):
    #         from fastapi.security.utils import get_authorization_scheme_param
    #         _, _authorization_token = get_authorization_scheme_param(_authorization)
    #
    # except Exception:
    #     logger.error(traceback.format_exc())
    #     return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={"error": "Authorization error, try loging again ..."})

    # logger.info(f"user params {params} for {user_id}")
    _event_data: typing.Union[None, ScrapeEventTable] = None
    try:
        if params:
            do_exist, blob_file_path = await check_scrape_event_exists(target_uri=params.website_uri)
            if do_exist:
                # load the json-data in memory
                fetched_json_data = await aio_read_file_data(blob_file_path=blob_file_path)
                if fetched_json_data:
                    fetched_json_data = json.loads(fetched_json_data)
                    instream_json_parser(_json_read_data=fetched_json_data)

            _event_data = await ScrapeEventTable.create(params=params)
            # _event_data = await ScrapeEventTable.get_event_details(event_id="91de5046-7dbc-11ef-9317-7295f59fdab3")
            if not _event_data:
                return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "Invalid data for creating Events ..."})

            _validator_params = {
                    "event_id": str(_event_data.event_id),
                    "user_id": request.cookies.get('user_id', None) if not params.user_id else params.user_id,
                    "website_uri": _event_data.website_uri,
                }

            if params.pages:
                _validator_params.update(**{
                    "page_limiter": params.pages
                })

            if params.proxy_string:
                _validator_params.update(**{
                    "proxy_string": params.proxy_string
                })

            ## micro-handling to perform scraping functionality
            scraping_event_params = EventScrapeData(
                **_validator_params
            )
            __response = await perform_scraping_handling(
                event_id=_event_data.event_id,
                event_params=scraping_event_params,
                fetched_json_data=fetched_json_data,
            )

            del fetched_json_data

    except Exception:
        logger.error(traceback.format_exc())
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "Format not found"})

    else:
        return JSONResponse(status_code=status.HTTP_200_OK, content={
            "message": f"Initiated the scraping event for website-uri = {params.website_uri} ...",
            "event_data": _event_data.serialize()
        })


@main_router.get("/events/{event_id}", dependencies=[Depends(AsyncJWTBearer())], response_model=EventMetadata)
async def fetch_event_details(
        request: Request,
        event_id: str,
):
    logger.info(f"fetching event metadata for {event_id = } ... ")

    try:
        # need to first authenticate the user
        if True:
            _event_data = await ScrapeEventTable.get_event_details(event_id=event_id)
            if not _event_data:
                return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "Event ID doesn't exists ..."})

    except Exception:
        logger.error(traceback.format_exc())
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"error": "Invalid event metadata ..."})

    else:
        _event_metadata = OrderedDict()
        for ele in _event_data.__dict__:
            if ele in ['_sa_instance_state', '__len__', 'event_metadata']:
                continue

            elif ele in ['start_date', 'end_date']:
                _event_metadata[ele] = str(_event_data.__dict__[ele])

            _event_metadata[ele] = str(_event_data.__dict__[ele])

        return JSONResponse(status_code=status.HTTP_200_OK, content={"event_metadata": _event_metadata})


@main_router.get("/recipient-session/success", dependencies=[Depends(AsyncJWTBearer())], response_model=None, response_model_exclude_none=True)
async def execute_scrape_checkout_session(event_id: str):
    """

    :param event_id:
    :return:
    """

    try:
        _event_metadata, _tranx_list = OrderedDict(), []
        _checkout_session = await ScrapeEventTable.get_event_details(event_id=event_id)

        # fetch the info store within DB on recorded transactions
        _fetch_tranx_session_data = await TransactionTable.fetch_tranx_metadata_by_event_id(
            event_id=event_id,
            blob_filename=_checkout_session.file_blob_path,
        )

        _metadata = {
                    "status": "CLOSED",
                    "recipient_delivery": True,
                    "is_active": False,
                    "counted_products": _checkout_session.counted_products,
                }

        # confirm the recipient session event
        if _checkout_session:
            if _fetch_tranx_session_data:
                for _tranx_data in _fetch_tranx_session_data:
                    _tranx_list.append(
                        {
                            "column_name": _fetch_tranx_session_data.column_name,
                            "existing_value": _fetch_tranx_session_data.existing_value,
                            "updated_value": _fetch_tranx_session_data.updated_value,
                        }
                    )

                _metadata.update(
                    **{
                        "metadata": _tranx_list
                    }
                )

            await ScrapeEventTable.update_event_metadata(
                event_id=event_id,
                **_metadata
            )

    except Exception as err:
        logger.error(traceback.format_exc())
        return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={
                    "message": "Failure encountered while performing Recipient execution ...",
                    "error": err
                }
            )

    else:
        return JSONResponse(status_code=status.HTTP_200_OK, content={
                "message": "Recipient successfully executed ...",
                "event_metadata": _event_metadata
            }
        )


@app.get("/health")
async def health():
    return "Health check on FastAPI Server!!"


app.include_router(
    main_router,
    prefix="",
    tags=["router"],
)

if __name__ == "__main__":
    import os

    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="debug",
        workers=os.cpu_count() * 4,
    )
