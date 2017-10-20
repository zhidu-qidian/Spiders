# coding: utf-8

from spiders.resource import get_cache_client
from spiders.resource import get_mongodb_database
from spiders.utilities import http
from spiders.utilities import rebuild_url, url_encode_params

KEY_RECEIVE = "spiders:schedule:config:id"
KEY_DOWNLOAD = "spider:download"
COL_CONFIGS = "spider_configs"
COL_CHANNELS = "spider_channels"
COL_REQUESTS = "v1_request"
COL_NEWS = "v1_news"
COL_ATLAS = "v1_atlas"
COL_VIDEO = "v1_video"
COL_JOKE = "v1_joke"
COL_PICTURE = "v1_picture"
COL_ADVERTISEMENT = "spider_advertisements"

redis = get_cache_client(db=2)
db_third_party = get_mongodb_database("thirdparty", "third")


def request_from_config_request(r):
    """ create http.Request from config.request """
    params = dict()
    headers = r["headers"]
    user_agent = headers.get("user_agent")
    if not user_agent:
        if r["user_agent_type"] == "pc":
            user_agent = http.get_default_browser()
        else:
            user_agent = http.get_default_mobile()
    else:
        del r["headers"]["user_agent"]
    if not headers:
        headers = None
    params["headers"] = headers
    params["user_agent"] = user_agent
    method = r["method"]
    params["method"] = method
    params["body"] = None
    url = r["url"]
    if method == "POST":
        params["body"] = url_encode_params(r["params"])
    elif method == "GET":
        if r["params"]:
            url = rebuild_url(r["url"], r["params"])
    else:
        raise ValueError("Only support GET or POST")
    return http.Request(url=url, **params)


def is_advertisement(md5, url):
    query = {"$or": [{"url": url}, {"md5": md5}]}
    count = db_third_party[COL_ADVERTISEMENT].count(query)
    return True if count > 0 else False
