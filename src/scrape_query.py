# -*- coding: utf-8 -*-
"""

@Filename : scrape query handler
@created :  Sept 28 11:42 2020
@project: atlys-interview-assignment
@author : Nikkhil Butola
"""
import datetime

"""
target website uri - https://dentalstall.com/shop/
for each other target uri [recurrent pages] - https://dentalstall.com/shop/page/1

paginator class
"""

import logging
import typing
import aiofiles
import pandas as pd
from lxml import html
from bs4 import BeautifulSoup, Tag
from urllib.request import Request, urlopen
import aiohttp
import os
import random
import pprint
import traceback
from pydantic_serializer import EventScrapeData
from collections import OrderedDict
import typing
import uuid
import traceback
import json
import pathlib
from constants import df_index_columns
from db import ScrapeEventTable


## configure the base logger settings for logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
loggingFormat = "[%(filename)s: %(lineno)s- %(funcName)11s() ] %(asctime)s: %(name)s:%(levelname)s %(message)s"
logging.basicConfig(format=loggingFormat)

# setting the pd dataframe maximum width
pd.set_option('display.max_colwidth', None)
limit_page_counter = 1  ## default value for limit page counter[need to set as env]

__agent_header_list = [
    'Mozilla/5.0 (Windows; U; Windows NT 6.1; x64; fr; rv:1.9.2.13) Gecko/20101203 Firebird/3.6.13',
    'Mozilla/5.0 (compatible, MSIE 11, Windows NT 6.3; Trident/7.0; rv:11.0) like Gecko',
    'Mozilla/5.0 (Windows; U; Windows NT 6.1; rv:2.2) Gecko/20110201',
    'Opera/9.80 (X11; Linux i686; Ubuntu/14.10) Presto/2.12.388 Version/12.16',
    'Mozilla/5.0 (Windows NT 5.2; RW; rv:7.0a1) Gecko/20091211 SeaMonkey/9.23a1pre'
]

## defined the Agent Header identifier for secure protocol
AGENT_HEADER = {'User-Agent': random.choice(__agent_header_list), 'X-Requested-With': 'XMLHttpRequest'}
logger.info(AGENT_HEADER)

__init_website_uri = "https://dentalstall.com/shop/"


async def __perform_query_search(*, session: aiohttp, search_href: str) -> typing.Union[None, Tag]:
    ## handling to scrape persistive information from INIT_WEBSITE_URI
    soup_query_response: typing.Union[None, Tag] = None
    try:
        async with session.get(search_href) as scrape_response:
            scrape_response = await scrape_response.read()

            # scrape_authorisation = urlopen(__init_request).read()  # performing web authorisation for request uri
            soup_query_response = BeautifulSoup(
                scrape_response.decode('utf-8'),
                'html.parser'
            )  # conceive the HTML format response on scraped website

        ## retry handlin' on search web-query post N seconds

    except Exception:
        logger.error(traceback.format_exc())
        return None

    else:
        return soup_query_response


"""
need to perform query filter on displayed product on init_query website
product-metadata -> product_name: str, published_price: union[int, str], associated_images: List['uri': str]

restricted options for querying:
    - limit the scrape processing by N: no of page to-be scraped
    - query filter by addon - proxy string param {presumption: product_tag, updated_by, by_review_quantifier, price_cap, discount_offered}
"""


async def ___execute_query_scraper_builder(*, session: aiohttp, soup_query_response: Tag,
                                           __pg_product_mapper: typing.List[typing.Dict],
                                           page_idx: typing.Union[None, int] = 1,
                                           __paginator_index: typing.Union[None, typing.List] = None):
    global limit_page_counter

    try:
        if page_idx != 1 and not soup_query_response:
            page_idx = page_idx + 1
            __followed_page_href = "https://dentalstall.com/shop/page/{0}".format(page_idx)
            print(__followed_page_href)

            try:
                if __recurring_query_resp := __followed_page_href and await __perform_query_search(
                        session=session,
                        search_href=__followed_page_href):
                    return await ___execute_query_scraper_builder(
                        soup_query_response=__recurring_query_resp,
                        __pg_product_mapper=__pg_product_mapper,
                        page_idx=page_idx,
                        __paginator_index=__paginator_index,
                    )

            except Exception:
                raise Exception

        elif not soup_query_response:
            return []

        try:
            ## keep track on website/uri paginator identifier to scrape products metadata by page-limit
            if __content_paginator := not __paginator_index and soup_query_response.select("nav ul li",
                                                                                           class_="woocommerce-paginator"):
                __paginator_index = sorted(
                    [int(_iter.get_text()) for _iter in __content_paginator if _iter.get_text().isnumeric()],
                    reverse=False)

            ## perform the scraper limit handlin' on target uri address
            if __paginator_index and limit_page_counter != 1:
                if not limit_page_counter in range(__paginator_index[0], __paginator_index[-1] + 1):
                    limit_page_counter = __paginator_index[
                        -1]  ## setting the limit_page_counter index to last paginator val for uri

            else:
                limit_page_counter = 1
                paginator_scraping = False

        except Exception:
            logger.error(traceback.format_exc())
            raise Exception

        # print(__paginator_index, " ", page_idx)
        while page_idx <= limit_page_counter:
            ## caution handlin' to scrape all enlist products pagewise,
            ## and deduce multi-FOR handlin -> WHILE operator sujective
            if scraped_product_info := soup_query_response.findAll("div", class_=["product-inner clearfix"]):
                try:
                    __product_iterator: typing.Union[None, typing.Iterator] = iter(scraped_product_info)

                except Exception:
                    raise Exception

            else:
                __product_iterator = None

            try:
                paginator_scraping: bool = True
                ## scrape the identified metadata for products enlisted on target uri
                _product: typing.Union[None, Tag] = None
                while _product := __product_iterator and next(
                        __product_iterator, None
                ):
                    __product_hash_mapper, __meta_images = OrderedDict(list()), list()
                    # print(_product)

                    ## regex handlin' to omit the noisy followed characters in product images link
                    import re  ## contextual handlin' import
                    regex_qualifier = r"\s*\d+w$"
                    _product_attrs = _product.select("img")[0].attrs
                    if __fetch_assoc_img_links := _product_attrs.get(
                            "data-lazy-srcset") if "data-lazy-srcset" in _product_attrs else _product_attrs.get(
                        "data-lazy-src"):
                        __meta_images.extend([link.split(re.search(regex_qualifier, link)[0])[0].strip() if re.search(
                            regex_qualifier, link) else link.strip() for link in __fetch_assoc_img_links.split(',')])
                        # print(__meta_images)

                    else:
                        print(_product.select("img")[0].attrs)

                    __product_hash_mapper["product_identifier"] = str(uuid.uuid1())
                    __product_hash_mapper["page_id"] = page_idx
                    __product_hash_mapper["product_description"] = _product.select("h2")[0].get_text().strip()

                    ## if not discount offered on product
                    if product_price := _product.select("del span bdi"):
                        __product_hash_mapper["published_price"] = product_price[0].get_text()

                    elif product_price := _product.select("span bdi"):
                        __product_hash_mapper["published_price"] = product_price[0].get_text()

                    else:
                        __product_hash_mapper["published_price"] = 0.00

                    ## if products discounted value exists
                    if discount_price := _product.select("ins span"):
                        __product_hash_mapper["discounted_price"] = discount_price[0].get_text()

                    else:
                        __product_hash_mapper["discounted_price"] = __product_hash_mapper["published_price"]

                    __product_hash_mapper["linked_images"] = __meta_images
                    __pg_product_mapper.append(__product_hash_mapper)

                page_idx += 1
                if paginator_scraping:
                    __followed_page_href = "https://dentalstall.com/shop/page/{0}".format(page_idx)
                    print(__followed_page_href)

                    if __recurring_query_resp := __followed_page_href and await __perform_query_search(
                            session=session,
                            search_href=__followed_page_href):
                        return await ___execute_query_scraper_builder(
                            session=session,
                            soup_query_response=__recurring_query_resp,
                            __pg_product_mapper=__pg_product_mapper,
                            page_idx=page_idx,
                            __paginator_index=__paginator_index,
                        )

                    ## if execption intercepted or request uri not found, skip current page and icrement page_idx
                    else:
                        page_idx += 1
                        __followed_page_href = "https://dentalstall.com/shop/page/{0}".format(page_idx)
                        return await ___execute_query_scraper_builder(
                            session=session,
                            soup_query_response=__recurring_query_resp,
                            __pg_product_mapper=__pg_product_mapper,
                            page_idx=page_idx,
                            __paginator_index=__paginator_index,
                        )

            except (StopIteration, Exception):
                logger.error(traceback.format_exc())

    except Exception:
        logger.error(traceback.format_exc())

    else:
        return __pg_product_mapper


# prod_metadata_df = pd.DataFrame(__pg_product_mapper, columns=df_index_columns)
# prod_metadata_df.reset_index()
# _json = json.loads(prod_metadata_df.to_json())

async def __write_json_to_file(*, event_id: str,  data_dump: typing.List[typing.Dict], blob_filename: str) -> bool:
    """
    write the json metadata to file blob storage locally
    """
    if data_dump:
        try:
            __root_blob_path: pathlib.Path = pathlib.Path(__file__).parent.joinpath('local-file-blob')
            __root_blob_path.mkdir(parents=True, exist_ok=True)
            __blob_filename = os.path.join(__root_blob_path, blob_filename)

            ## create the file-blob and write the scraped json data to it
            async with aiofiles.open(__blob_filename, mode="w+", buffering=1) as _fp_buffer:
                await _fp_buffer.write(json.dumps(data_dump, indent=4))

        except (IsADirectoryError, Exception):
            logger.error(traceback.format_exc())
            return False

        else:
            return True


async def __update_scrape_event_metadata(*, event_id: uuid.uuid1, **kwargs):
    try:
        if event_data := await ScrapeEventTable.get_event_details(event_id=str(event_id)):
            __started_at = event_data.start_date
            __ended_at = datetime.datetime.utcnow()
            duration_diff = __ended_at - __started_at
            duration_diff = duration_diff.total_seconds()
            kwargs["durations"] = int(duration_diff)
            kwargs["end_date"] = __ended_at

            _response = await ScrapeEventTable.update_event_metadata(
                event_id=str(event_id),
                **kwargs,
            )

    except Exception:
        logger.error(traceback.format_exc())
        return False

    else:
        return _response


async def perform_scraping_handling(
        event_id: int,
        event_params: EventScrapeData
):
    logger.info(f"Performing scraping event with metadata as {event_params} ...")
    global limit_page_counter
    try:
        # TODO: need to first authenticate the user
        """
            1. initiate Request mode on event-scraping uri
            2. once the response captured, forward the page-response to restricted query executor
            3. depending on the Optional params, perform subjected actions, proxy-string [to be re-evaluated]
            4. write the builder query response to JSON file, and yield the local blob storage address
                4.1 for file revision history record, file_name as `datetime stamp + event_id[uuid].json`
                    to maintain the unique records for rewrite
            5. once the above procedure performed as per needed, pseudo-bake the handling on Event-architecture recipient
                service delivery, actual architecture -> [SQS <-> SNS, AWS Lambda event trigger, recipient delivery via SES]
        """

        if not event_params.website_uri:
            raise Exception

        __pg_product_mapper: typing.List = list()
        limit_page_counter = event_params.page_limiter

        async with aiohttp.ClientSession(headers=AGENT_HEADER, timeout=aiohttp.ClientTimeout(10)) as session:
            if bs4_query_response := await __perform_query_search(session=session, search_href=__init_website_uri):
                __final_mapper_response = await ___execute_query_scraper_builder(
                    session=session,
                    soup_query_response=bs4_query_response,
                    __pg_product_mapper=__pg_product_mapper,
                )
                del __pg_product_mapper

            """
            write the json metadata to file blob storage locally
            """
            __blob_filename: str = "".join([str(datetime.datetime.utcnow()), "-", str(event_params.event_id), ".json"])
            if __final_mapper_response:
                _is_writen = await __write_json_to_file(
                    event_id=str(event_params.event_id),
                    data_dump=__final_mapper_response,
                    blob_filename=__blob_filename,
                )

                """
                once the data written to blob file, update the scrape event metadata
                """
                if _is_writen:
                    await __update_scrape_event_metadata(
                        event_id=event_params.event_id,
                        **{
                            "file_blob_path": __blob_filename,
                            "status": "SCRAPED",
                        }
                    )
                    print("metadata successfully updated ...")

        return dict(status_code=200,
                    content={
                        "msg": f"Successfully performed event-scraping and updated metadata for event_id {event_params.event_id} as required ..."
                    }
                )

    except Exception:
        logger.error(traceback.format_exc())
        return dict(status_code=404, content={"error": "Invalid event metadata to initiate scraping-event ..."})


__all__ = ["perform_scraping_handling", "__init_website_uri"]
