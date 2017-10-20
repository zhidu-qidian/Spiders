# coding:utf-8
import time
from spiders.utilities import http, format_datetime_string, clean_date_time
from spiders.parsers.feed import FeedParser
from spiders.business.utils import redis
from spiders.models import NewsFields, ListFields, ForeignFields, AtlasFields
from spiders.utilities import get_string_md5, utc_datetime_now
from pymongo.errors import DuplicateKeyError
from urllib import quote
from pymongo import MongoClient
from spiders.business.utils import db_third_party as db

PROCEDURE_LIST_TASK = 0  # 完成列表页解析状态


def general_list(list_page_info):
    def _request_doc_from_config_channel(config):
        doc = dict()
        doc["channel"] = config["channel"]
        doc["config"] = str(config["_id"])
        doc["form"] = config["form"]
        doc["site"] = config["site"]
        doc["time"] = utc_datetime_now()
        doc["fields"] = dict()
        doc["unique"] = ""
        doc["procedure"] = -1
        return doc

    content = http.download_html(url=list_page_info["url"])
    result = FeedParser(document=content, crawler=list_page_info["crawler"], url=list_page_info["url"])
    ids = list()
    for item in result:
        middle = _request_doc_from_config_channel(list_page_info)
        fields = ListFields()
        fields.url = item["url"]
        fields.title = item.get("title", "")
        fields.publish_time = format_datetime_string(item.get("publish_time", ""))
        fields.publish_ori_name = item.get("publish_site") or item.get("author", "")
        fields.abstract = item.get("abstract", "")
        fields.tags = item.get("keywords", "")
        fields.html = item.get("html", "")
        if item.get("thumb"):
            fields.thumbs.append(item["thumb"])
        middle["list_fields"] = fields.to_dict()
        middle["pages"] = [{"url": item["url"], "html": ""}]
        middle["unique"] = item["url"]  # 以 url 作为唯一性约束,避免重复抓取 TODO: 归一化url
        middle["procedure"] = PROCEDURE_LIST_TASK
        try:
            r = db.v1_request.insert_one(middle)  # fixme: 插入失败
        except DuplicateKeyError:
            print "DuplicateKeyError"
        except Exception as e:
            print e
        else:
            print "MONGO Insert Success"
            ids.append(str(r.inserted_id))

    next_key = "v1:spider:task:download:id"
    if not ids:
        return
    if isinstance(ids, list):
        redis.sadd(next_key, *ids)
        print "REDIS Add Success"
    elif id:
        redis.sadd(next_key, ids)
        print "REDIS Add Success"
    else:
        print "REDIS Add Faild"


def laozongyi():
    # DONE
    print "Task Laozongyi"
    url_template = "http://www.laozongyi.com/yinshi/yzc_{num}.html"
    for i in range(1, 39):
        url = url_template.format(num=i)
        config = dict()
        config["url"] = url
        config["crawler"] = "laozongyi_com"
        config["channel"] = "59ad15ba921e6d6f0906a719"  # channel id
        config["_id"] = "59ad15ba921e6d6f0906a71a"  # config id
        config["form"] = "news"
        config["site"] = "59ad1534921e6d6f0a06a71b"  # site id
        print config
        time.sleep(1)
        try:
            general_list(config)
        except Exception as e:
            print "ERROR:", e


def xinshipu():
    # DONE
    print "Task xinshipi-com"
    url_template = "http://www.xinshipu.com/caipu/114072/?page={num}"
    for i in range(1, 16):
        url = url_template.format(num=i)
        config = dict()
        config["url"] = url
        config["crawler"] = "xinshipu_com"
        config["channel"] = "59ad17cd921e6d6f0a06a71c"  # channel id
        config["_id"] = "59ad17cd921e6d6f0a06a71d"  # config id
        config["form"] = "news"
        config["site"] = "59ad1712921e6d6f0906a720"  # site id
        print config
        time.sleep(1)
        try:
            general_list(config)
        except Exception as e:
            print "ERROR:", e


def cn_com_99():
    # DONE
    print "Task 99-com-cn"
    url_template = "http://fk.99.com.cn/chanhys/3250-{num}.html"
    for i in range(1, 23):
        url = url_template.format(num=i)
        config = dict()
        config["url"] = url
        config["crawler"] = "99_com_cn"
        config["channel"] = "59ad16d4921e6d6f0906a71d"  # channel id
        config["_id"] = "59ad16d4921e6d6f0906a71e"  # config id
        config["form"] = "news"
        config["site"] = "59ad1680921e6d6f0906a71c"  # site id
        print config
        time.sleep(1)
        try:
            general_list(config)
        except Exception as e:
            print "ERROR:", e


def club_autohome():
    print "Task club-autohome"
    url_template = "http://club.autohome.com.cn/JingXuan/104/{num}"
    for i in range(2, 21):
        url = url_template.format(num=i)
        config = dict()
        config["url"] = url
        config["crawler"] = "autohome_club"
        config["channel"] = "59acc751921e6d6f0906a710"  # channel id
        config["_id"] = "59acc751921e6d6f0906a711"  # config id
        config["form"] = "news"
        config["site"] = "591ebb17ccb1365d651a43b8"  # site id
        print config
        time.sleep(1)
        try:
            general_list(config)
        except Exception as e:
            print "ERROR:", e


def chebiaow():
    print "Task chebiaow"
    url_template = "http://www.chebiaow.com/chemo/list_{num}.html"
    for i in range(2, 9):
        url = url_template.format(num=i)
        config = dict()
        config["url"] = url
        config["crawler"] = "chebiaow_com"
        config["channel"] = "59acc838921e6d6f0a06a711"  # channel id
        config["_id"] = "59acc838921e6d6f0a06a712"  # config id
        config["form"] = "news"
        config["site"] = "59acc7e3921e6d6f0a06a710"  # site id
        print config
        time.sleep(1)
        try:
            general_list(config)
        except Exception as e:
            print "ERROR:", e


def chemo_7160():
    print "Task chemo-7160"
    url_template = "http://www.7160.com/lianglichemo/list_8_{num}.html"
    for i in range(2, 186):
        url = url_template.format(num=i)
        config = dict()
        config["url"] = url
        config["crawler"] = "7160_com"
        config["channel"] = "59acc8ab921e6d6f0906a716"  # channel id
        config["_id"] = "59acc8ab921e6d6f0906a717"  # config id
        config["form"] = "atlas"
        config["site"] = "5875f3893deaeb61dd2e2897"  # site id
        print config
        time.sleep(1)
        try:
            general_list(config)
        except Exception as e:
            print "ERROR:", e


def chemo_mmonly():
    print "Task chemo-mmonly"
    url_template = "http://www.mmonly.cc/tag/cm/{num}.html"
    for i in range(2, 15):
        url = url_template.format(num=i)
        config = dict()
        config["url"] = url
        config["crawler"] = "mmonly_cc"
        config["channel"] = "59acc90a921e6d6f0a06a714"  # channel id
        config["_id"] = "59acc90a921e6d6f0a06a715"  # config id
        config["form"] = "atlas"
        config["site"] = "57edd20afe8eca4bb431693c"  # site id
        print config
        time.sleep(1)
        try:
            general_list(config)
        except Exception as e:
            print "ERROR:", e


def bitauto():
    print "Task bitauto"
    url_template = "http://www.bitauto.com/newslist/a1832-{num}.html"
    for i in range(1, 23):
        url = url_template.format(num=i)
        config = dict()
        config["url"] = url
        config["crawler"] = "bitauto_com"
        config["channel"] = "59b0e445921e6d6f0a06a720"  # channel id
        config["_id"] = "59b0e445921e6d6f0a06a721"  # config id
        config["form"] = "news"
        config["site"] = "59b0e3ed921e6d6f0a06a71f"  # site id
        print config
        time.sleep(1)
        try:
            general_list(config)
        except Exception as e:
            print "ERROR:", e


def ifeng_auto():
    print "Task Ifeng-Auto"
    url_template = "http://auto.ifeng.com/youji/{num}.shtml"
    for i in range(1, 13):
        url = url_template.format(num=i)
        config = dict()
        config["url"] = url
        config["crawler"] = "ifeng_youji"
        config["channel"] = "59b0e3cb921e6d6f0906a721"  # channel id
        config["_id"] = "59b0e445921e6d6f0a06a721"  # config id
        config["form"] = "news"
        config["site"] = "57c64e49fe8eca2b7946609a"  # site id
        print config
        time.sleep(1)
        try:
            general_list(config)
        except Exception as e:
            print "ERROR:", e


def news18a():
    print "Task News18a"
    url_template = "http://auto.news18a.com/news/more_list_column_631_{num}.html"
    for i in range(1, 11):
        url = url_template.format(num=i)
        config = dict()
        config["url"] = url
        config["crawler"] = "news18a_auto"
        config["channel"] = "59acc9a1921e6d6f0a06a718"  # channel id
        config["_id"] = "59acc9a1921e6d6f0a06a719"  # config id
        config["form"] = "news"
        config["site"] = "59acc95b921e6d6f0a06a717"  # site id
        print config
        time.sleep(1)
        try:
            general_list(config)
        except Exception as e:
            print "ERROR:", e


def xiachufang():
    print "Task xiachufang"
    url_template = "http://www.xiachufang.com/category/30048/?page={num}"
    for i in range(1, 11):
        url = url_template.format(num=i)
        config = dict()
        config["url"] = url
        config["crawler"] = "xiachufang_com"
        config["channel"] = "59b0f8a8921e6d6f0906a725"  # channel id
        config["_id"] = "59b0f8a8921e6d6f0906a726"  # config id
        config["form"] = "news"
        config["site"] = "59b0f843921e6d6f0a06a726"  # site id
        print config
        time.sleep(1)
        try:
            general_list(config)
        except Exception as e:
            print "ERROR:", e


def yxlady():
    print "Task yxlady"
    url_template = "https://fitness.yxlady.com/List_95_{num}.shtml"
    for i in range(1, 11):
        url = url_template.format(num=i)
        config = dict()
        config["url"] = url
        config["crawler"] = "yxlady_com"
        config["channel"] = "59b0f7fd921e6d6f0a06a723"  # channel id
        config["_id"] = "59b0f7fd921e6d6f0a06a724"  # config id
        config["form"] = "news"
        config["site"] = "59b0f76c921e6d6f0906a724"  # site id
        print config
        time.sleep(1)
        try:
            general_list(config)
        except Exception as e:
            print "ERROR:", e


if __name__ == "__main__":
    # laozongyi()
    # cn_com_99()
    # xinshipu()
    # club_autohome()
    # chebiaow()
    # chemo_7160()
    # chemo_mmonly()
    # bitauto()
    # ifeng_auto()
    # news18a()
    xiachufang()
    yxlady()
