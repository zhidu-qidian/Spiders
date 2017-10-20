# coding: utf-8

from datetime import datetime
import logging
import urlparse
import urllib

from bson import ObjectId
import xmltodict

from spiders.business.utils import db_third_party as db
from spiders.business.utils import COL_CHANNELS, COL_CONFIGS, COL_REQUESTS
from spiders.business.utils import redis
from spiders.models import ListFields
from spiders.utilities import utc_datetime_now


COL_WEIXIN_MESSAGE = "weixin_message"
KEY = "weixin:message:id"
KEY_DOWNLOAD_TASK = "v1:spider:task:download:id"


def get_channel_config(nick_name):
    weixin_site_id = "57bab42eda083a1c19957b1f"
    channel = db[COL_CHANNELS].find_one({"name": nick_name, "site": weixin_site_id})
    config = db[COL_CONFIGS].find_one({"channel": str(channel["_id"])})
    return channel, config


def get_channel_config_from_user_name(nick_name):
    channel, config = None, None
    if not nick_name:
        return channel, config
    channel, config = get_channel_config(nick_name)
    return channel, config


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


def clean_permanent_url(url):
    o = urlparse.urlparse(url)
    query = urlparse.parse_qs(o.query)
    keys = ["chksm"]
    for key in keys:
        if key in query:
            del query[key]
    new = list(o)
    new[4] = urllib.urlencode(query, doseq=True)
    new[5] = ""
    return urlparse.urlunparse(tuple(new))


def crop_permanent_url(url):
    index = url.find("&chksm=")
    return url[:index] if index >= 0 else url


def get_list_fields_from_message(content):
    result = list()
    content = xmltodict.parse(content)
    items = content["msg"]["appmsg"]["mmreader"]["category"]["item"]
    if isinstance(items, dict):
        items = [items]
    for item in items:
        fields = ListFields()
        fields.title = item["title"]
        fields.url = crop_permanent_url(item["url"])
        fields.publish_time = datetime.\
            fromtimestamp(int(item["pub_time"])).strftime("%Y-%m-%d %H:%M:%S")
        fields.abstract = item["digest"]
        result.append(fields)
    return result


def process(message):
    documents = list()
    nick_name = message["__nick_name"]
    channel, config = get_channel_config_from_user_name(nick_name)
    if not channel:  # todo: 如果查找不到公众号相关信息，需处理
        logging.error("no hao: %s relate channel config info" % nick_name)
        return documents
    content = message["Content"]
    items = get_list_fields_from_message(content)
    for item in items:
        document = request_doc_from_config_channel(config, channel)
        list_fields = item
        document["list_fields"] = list_fields.to_dict()
        document["pages"] = [{"url": list_fields.url, "html": ""}]
        document["unique"] = list_fields.url
        document["procedure"] = 0
        documents.append(document)
    return documents


def show(data):
    for k, v in data.items():
        print k, ":", v
    print "*" * 120


def main():
    while 1:
        _, _id = redis.brpop(KEY)
        logging.info("start process %s" % _id)
        message = db[COL_WEIXIN_MESSAGE].find_one({"_id": ObjectId(_id)})
        try:
            documents = process(message=message)
        except Exception as e:
            logging.error(e.message, exc_info=True)
            logging.error("error _id: %s" % _id)
        else:
            for document in documents:
                try:
                    result = db[COL_REQUESTS].insert_one(document)
                except Exception as e:
                    logging.error(e.message)
                else:
                    r_id = str(result.inserted_id)
                    redis.sadd(KEY_DOWNLOAD_TASK, r_id)
                    logging.info("process weixin request id: %s" % r_id)


if __name__ == "__main__":
    main()
