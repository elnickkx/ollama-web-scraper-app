# -*- coding: utf-8 -*-
"""

@Filename : redis in-memory utility
@created :  Sept 29 11:17 2020
@project: atlys-interview-assignment
@author : Nikkhil Butola
"""
import json
import os.path
import traceback
import aiofiles
from rejson import Client, Path
import typing
from collections import OrderedDict
import logging
import pathlib

"""
    - need to define the redis in-memory DB connection
    - supported functions to perform CRUD opertions
    - JSON data parser for serializing the product records information
        {redis_db_key : {json_key1: json_value1, json_key2: json_value2}}
        for instance: {"product_title": {"product_price": "price_value"}}
        
    - need to query the DB-scrape_event table, fetch the latest record against the target-website uri
        if not existing, proceed with existin' workflow design
        else:
        - navigate to the respective blob filename carrying the intensified records :: product metadata
        - parse the entire json record into simplified order
            - if the price against target product_title different from existin' ones
                perform the update entity operation, and modify the in-memory loaded json records
                
            - ones waived through the in-memory workflow design, store the records to new blob storage
            - record the transaction history against the scrape event_id and user_id
    
    - in-memory cache integration, docker-command to execute the redisjson container locally:
        - docker run -d --name redis-stack -p 6379:6379 -p 8001:8001 -e REDIS_ARGS="--requirepass mypassword" redis/redis-stack:latest
        - docker run -it container_id
        - docker exec -it container_id redis-cli
         
"""

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
loggingFormat = "[%(filename)s: %(lineno)s- %(funcName)11s() ] %(asctime)s: %(name)s:%(levelname)s %(message)s"
logging.basicConfig(format=loggingFormat)

redis_client = Client(host='localhost', port=6379, decode_responses=True)


def set_memcached_obj_data(*, parent_obj: str,
                           json_object: typing.Dict[str, typing.Union[str, int, float]]):
    logger.info(f"Setting the json data for {parent_obj = } in memcached store ...")
    if redis_client.jsonset(name=parent_obj, path=Path.rootPath(),
                            obj=json_object):  ## Path.rootPath -- defines the redis stores root path
        return True


def get_memcached_obj_data(*, parent_obj: str, object_attr: typing.Union[None, str] = None,
                           compare_to: typing.Union[None, int, float] = None):
    try:
        if _memcached_val := redis_client.jsonget(parent_obj, Path('.{}'.format(object_attr))):
            if str(compare_to) != str(_memcached_val):
                return _memcached_val, compare_to

            else:
                return None, None

        return None, None

    except Exception:
        logger.error(traceback.format_exc())
        raise None


def instream_json_parser(*, _json_read_data: typing.List[
    typing.Dict[str, typing.Union[typing.List, typing.Dict[str, str]]]]):
    if not _json_read_data:
        return []

    try:
        __redis_comp_data_fmt: typing.List[typing.Dict[str, str]] = list(OrderedDict())
        for _idx, dict_obj in enumerate(_json_read_data):
            __parent_obj: str = dict_obj.get("product_title", "product_{}".format(_idx))
            __json_object: typing.Dict[str, typing.Union[int, float]] = {
                "product_price": dict_obj.get("discounted_price", 0.00),
                "_index": _idx
            }

            if set_memcached_obj_data(
                    parent_obj=__parent_obj,
                    json_object=__json_object,
            ):
                continue

    except (IndexError, Exception):
        logger.error(traceback.format_exc())
        raise Exception


async def aio_read_file_data(*, blob_file_path: str):
    try:
        # blob_file_path = "2024-09-29 17:38:15.533104-6c442248-7e89-11ef-b71e-7295f59fdab3.json"
        __root_blob_path: pathlib.Path = pathlib.Path(__file__).parent.joinpath('local-file-blob')
        if not os.path.exists(__root_blob_path):
            __root_blob_path.mkdir(parents=True, exist_ok=True)

        __blob_filename = os.path.join(__root_blob_path, blob_file_path)
        # read the scraped json data from blob file
        async with aiofiles.open(__blob_filename, mode="r", buffering=1) as _fp_buffer:
            _json_data = await _fp_buffer.read()

    except Exception:
        logger.error(traceback.format_exc())
        logger.info("Skipping the procedure to ingest the products record in memcached DB ...")
        return []

    else:
        return _json_data
