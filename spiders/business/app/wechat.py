# coding: utf-8

from datetime import datetime
import logging
import re
from time import sleep
import urlparse

from bs4 import BeautifulSoup
from bson import ObjectId

from spiders.business.utils import db_third_party as db
from spiders.business.utils import redis
from spiders.business.utils import COL_CHANNELS, COL_CONFIGS, COL_REQUESTS
from spiders.utilities import utc_datetime_now
from spiders.models import ListFields


LIST = "wechat_list"
ARTICLE = "wechat_detail"
METRIC = "wechat_metric"
COMMENT = "wechat_comment"


def get_data_list(sn):
    data = list()
    query = {"snarray": {"$all": [sn]}}
    items = db[LIST].find_one(query)
    if not items:
        return None
    app = items["app"]
    date = datetime.fromtimestamp(items["comm"]["datetime"])\
        .strftime("%Y-%m-%d %H:%M:%S")
    app["appmsgitem"]["datetime"] = date
    data.append(app["appmsgitem"])
    if app["ismulti"] == 1:
        for item in app["multiappmsgitemlist"]:
            item["datetime"] = date
            data.append(item)
    result = dict()
    for d in data:
        url = d["contenturl"]
        obj = urlparse.urlparse(url)
        params = urlparse.parse_qs(obj.query)
        if "sn" in params:
            result[params["sn"][0]] = d
    return result[sn]


def get_list_fields(sn):
    fields = ListFields()
    data = get_data_list(sn)
    if data:
        fields.title = data["title"]
        fields.abstract = data.get("digest", "")
        fields.url = data["contenturl"]
        fields.publish_time = data["datetime"]
        if data.get("cover"):
            fields.thumbs.append(data["cover"])
    else:
        logging.warning("sn not found in list: %s" % sn)
    return fields


def get_comment_id(html):
    match = re.search(r'var comment_id = "([0-9]{8,12})"', html)
    return match.group(1) if match else None


def request_doc_from_config_channel(config, channel):
    doc = dict()
    doc["channel"] = config["channel"]
    doc["config"] = str(config["_id"])
    doc["form"] = channel["form"]
    doc["site"] = channel["site"]
    doc["time"] = utc_datetime_now()
    doc["fields"] = dict()
    doc["unique"] = ""
    doc["procedure"] = -1
    return doc


def get_channel_config(hao):
    query = {"meta.name": hao, "site": "57bab42eda083a1c19957b1f"}
    channel = db[COL_CHANNELS].find_one(query)
    if not channel:
        return None, None
    config = db[COL_CONFIGS].find_one({"channel": str(channel["_id"])})
    if not config:
        return None, None
    return channel, config


def update_comment_id(_id, comment_id):
    db[ARTICLE].update_one({"_id": _id}, {"$set": {"comment_id": comment_id}})


def get_metrics(comment_id):
    metric = db[METRIC].find_one({"meta.comment_id": comment_id})
    if not metric:
        return 0, 0
    n_read = metric["appmsgstat"]["readnumber"]
    n_like = metric["appmsgstat"]["likenumber"]
    return n_read, n_like


def get_weixin_hao(html):
    soup = BeautifulSoup(html, "lxml")
    tag = soup.select_one("span.profile_meta_value")
    return tag.get_text().strip() if tag else None


def new_wechat_task(sn, debug=False):
    article = db[ARTICLE].find_one({"meta.sn": sn})
    hao = get_weixin_hao(article["html"])
    channel, config = get_channel_config(hao)
    if not channel:
        return None
    html = article["html"]
    list_fields = get_list_fields(sn)
    list_fields.html = html
    doc = request_doc_from_config_channel(config, channel)
    doc["list_fields"] = list_fields.to_dict()
    comment_id = get_comment_id(html)
    if comment_id:
        update_comment_id(article["_id"], comment_id)
        doc["list_fields"]["comment"] = {"id": comment_id}
        n_read, n_like = get_metrics(comment_id)
        doc["list_fields"]["n_read"] = n_read
        doc["list_fields"]["n_like"] = n_like
    doc["pages"] = [{"url": article["url"], "html": ""}]
    doc["unique"] = article["url"]
    doc["procedure"] = 0
    if debug:
        return doc
    try:
        result = db[COL_REQUESTS].insert_one(doc)
    except Exception:
        pass
    else:
        if result and result.inserted_id:
            w_id = str(result.inserted_id)
            logging.info("process weixin news %s" % w_id)
            return w_id
    return None


KEY_DOWNLOAD_TASK = "v1:spider:task:download:id"


def main():
    key = "v1:weixin:process"
    while 1:
        _, sn = redis.brpop(key)
        length = redis.llen(key)
        if length == 0:
            sleep(5)
        logging.info("Start process sn: %s" % sn)
        try:
            w_id = new_wechat_task(sn)
            if w_id:
                redis.sadd(KEY_DOWNLOAD_TASK, w_id)
        except Exception as e:
            logging.error(e.message, exc_info=True)


if __name__ == "__main__":
    main()
