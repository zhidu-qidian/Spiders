# coding: utf-8

""" app 抓取来源存储接口

1. 即刻进入爬虫 pipeline 相关步骤
2. 豌豆荚进入爬虫 pipeline 相关步骤
3. 微博存入 thirdparty weibo collection 并推 id 送到微博处理队列
"""

from datetime import datetime
from hashlib import md5
import json
import logging
from time import strftime, localtime
from types import UnicodeType

from bson import ObjectId
from tornado.web import RequestHandler
import tornado.web
import tornado.ioloop
import tornado.httpserver
import tornado.options
from pymongo.errors import DuplicateKeyError

from spiders.business.utils import db_third_party as db
from spiders.business.utils import COL_REQUESTS, COL_CONFIGS, COL_CHANNELS
from spiders.business.utils import redis
from spiders.models import ListFields

__author__ = "lixianyang"
__email__ = "705834854@qq.com"
__date__ = "2017-04-27 15:34"

COL_SITES = "spider_sites"


def str_from_timestamp(timestamp):
    return strftime("%Y-%m-%d %H:%M:%S", localtime(timestamp))


def fake_news_html(title, body):
    html = '''<html>
                <head></head>
                <body>
                    <div id="app_article_title">%s</div>
                    <div id="app_article_content">%s</div>
                </body>
            </html>''' % (title, body)
    return html


class BaseHandler(RequestHandler):
    @classmethod
    def is_valid(cls, *args, **kwargs):
        for filed in args:
            if not filed:
                return False
        return True

    @classmethod
    def get_meta_info(cls):
        raise NotImplementedError

    def get_fake_url(self, string):
        raise NotImplementedError

    @classmethod
    def get_fake_html(cls, title, body):
        raise NotImplementedError

    @classmethod
    def get_publish_time(cls, string):
        return str_from_timestamp(int(string) / 1000)

    @classmethod
    def get_procedure_code(cls):
        raise NotImplementedError

    @classmethod
    def get_queue_name(cls):
        raise NotImplementedError

    @classmethod
    def g_request(cls):
        doc = dict()
        site_id, channel_id, config_id = cls.get_meta_info()
        doc["channel"] = channel_id
        doc["config"] = config_id
        doc["form"] = "news"
        doc["site"] = site_id
        doc["time"] = datetime.utcnow()
        doc["fields"] = dict()
        doc["unique"] = ""
        doc["procedure"] = cls.get_procedure_code()
        return doc

    @classmethod
    def already_exist(cls, url):
        n = db[COL_REQUESTS].count({"unique": url})
        return True if n > 0 else False

    @staticmethod
    def store_request(doc):
        try:
            r = db[COL_REQUESTS].insert_one(doc)  # fixme: 插入失败
        except DuplicateKeyError:
            pass
        except Exception as e:
            logging.error(e.message, exc_info=True)
        else:
            return str(r.inserted_id)
        return None

    def post(self, *args, **kwargs):
        """存储app来源的数据"""
        title = self.get_body_argument("title", "")
        body = self.get_body_argument("html", "")
        publish_name = self.get_body_argument("source", "")
        publish_timestamp = self.get_body_argument("time", "")
        link = self.get_body_argument("url", "")
        author = self.get_body_argument("author", None)
        summary = self.get_body_argument("summary", None)
        if not self.is_valid(title, body, publish_name, publish_timestamp, link):
            message = "Not valid params"
            logging.warning(message)
            self.write({"message": message})
            return
        url = link if link else self.get_fake_url(body)
        if not url:
            message = "Not valid url"
            logging.warning(message)
            self.write({"message": message})
            return
        if self.already_exist(url):
            message = "Already exist"
            logging.info(message)
            self.write(message)
            return
        fields = ListFields()
        fields.url = link if link else self.get_fake_url(body)
        fields.html = self.get_fake_html(title, body)
        fields.publish_time = self.get_publish_time(publish_timestamp)
        fields.title = title
        fields.publish_ori_name = publish_name
        if summary:
            fields.abstract = summary
        doc = self.g_request()
        doc["list_fields"] = fields.to_dict()
        doc["pages"] = [{"url": fields.url, "html": ""}]
        doc["unique"] = fields.url
        _id = self.store_request(doc)
        if _id:
            message = "Store success %s" % _id
            logging.info(message)
            self.write({"message": message})
            redis.sadd(self.get_queue_name(), _id)
        else:
            message = "Store error"
            logging.warning(message)
            self.write({"message": message})


class WanDouJiaHandler(BaseHandler):
    BANS = {u"Pinkoi", u"别致", u"豆瓣东西", u"约瑟的粮仓", u"设计本装修"}

    @classmethod
    def is_valid(cls, title, body, name, timestamp, link):
        """判断四个字段都有效，且过滤掉指定来源的数据"""
        if not (title and body and name and timestamp):
            return False
        return False if name in cls.BANS else True

    @classmethod
    def get_meta_info(cls):
        return "57ac3802da083a1c19957b1b", "57ac38feda083a1c19957b1c", "5900594fccb136704ed6373e"

    def get_fake_url(self, string):
        if isinstance(string, UnicodeType):
            string = string.encode("utf-8")
        return "http://www.fakewandoujia.com/" + md5(string).hexdigest()

    @classmethod
    def get_fake_html(cls, title, body):
        html = '''<html>
                    <head></head>
                    <body>
                        <div id="app_article_title">%s</div>
                        <div id="app_article_content">%s</div>
                    </body>
                </html>''' % (title, body)
        return html

    @classmethod
    def get_procedure_code(cls):
        return 0  # 完成列表页解析状态

    @classmethod
    def get_queue_name(cls):
        key_download_task = "v1:spider:task:download:id"
        return key_download_task


class JiKeHandler(BaseHandler):
    @classmethod
    def is_valid(cls, title, body, name, timestamp, link):
        """判断四个字段都有效，且过滤掉指定来源的数据"""
        if not (title and timestamp and link):
            return False
        return True

    @classmethod
    def get_meta_info(cls):
        return "57ac3802da083a1c19957b1b", "57ac392ada083a1c19957b1d", "5900594fccb136704ed6373f"

    def get_fake_url(self, string):
        return self.get_body_argument("link")

    @classmethod
    def get_fake_html(cls, title, body):
        return ""

    @classmethod
    def get_procedure_code(cls):
        return 0  # 完成列表页解析状态

    @classmethod
    def get_queue_name(cls):
        key_download_task = "v1:spider:task:download:id"
        return key_download_task


class WeiBoHandler(RequestHandler):
    def post(self, *args, **kwargs):
        """存储微博app来源的数据

        news:json_data
        """
        item = self.get_body_argument("news", None)
        item = json.loads(item)
        if db["weibo"].count({"id": item["status"]["id"]}) > 0:
            message = "Already exists"
            self.write({"message": message})
        else:
            item["id"] = item["status"]["id"]
            item["time"] = datetime.now()
            item["procedure"] = 0
            try:
                result = db["weibo"].insert_one(item)
            except Exception as e:
                self.write({"message": e.message})
                return
            _id = str(result.inserted_id)
            self.do_next(_id)
            logging.info("Store weibo id: %s" % _id)
            self.write({"message": _id})

    @classmethod
    def do_next(cls, _id):
        key = "v1:weibo:process"
        redis.lpush(key, _id)


class WeixinHandler(RequestHandler):
    def is_valid(self):
        token = self.get_argument("token")
        return token == "weixin"

    def get(self, *args, **kwargs):
        """ 这里根据是否传参数 hao 判断是要获取微信号还是报告失效的微信号"""
        key = "v1:weixin:config:id"
        unused_key = "v1:unused:weixin:hao"
        if not self.is_valid():
            self.write("")
            return
        hao = self.get_query_argument("hao", None)
        if hao:
            redis.sadd(unused_key, hao)
            self.write("")
            return
        _id = redis.spop(key)
        if not _id:
            self.write("")
            return
        config = db[COL_CONFIGS].find_one({"_id": ObjectId(_id)})
        channel = db[COL_CHANNELS].find_one({"_id": ObjectId(config["channel"])})
        self.write(channel["meta"]["name"])

    def post(self, *args, **kwargs):
        if not self.is_valid():
            self.write("")
            return
        key = "v1:weixin:process"
        _id = self.get_argument("id")
        redis.lpush(key, _id)
        self.write({"code": 200})


class ClickHandler(RequestHandler):
    KEY = "v1:weixin:click:article:number"

    def is_valid(self):
        token = self.get_argument("token")
        return token == "weixin"

    def get(self, *args, **kwargs):
        if not self.is_valid():
            self.write("")
            return
        number = redis.get(self.KEY)
        if number is None:
            number = ""
        self.write(number)

    def post(self, *args, **kwargs):
        if not self.is_valid():
            self.write({"code": 404})
            return
        number = self.get_argument("number")
        redis.set(self.KEY, number)
        self.write({"code": 200})


class SiteHandler(RequestHandler):
    def get(self, *args, **kwargs):
        name = self.get_query_argument("name")
        query = {"name": name}
        sites = list(db[COL_SITES].find(query))
        for site in sites:
            site["_id"] = str(site["_id"])
        self.write({"data": sites})


class ChannelHandler(RequestHandler):
    def get(self, *args, **kwargs):
        site = self.get_query_argument("site")
        page = int(self.get_query_argument("page", 0))
        n = int(self.get_query_argument("n", 20))
        skip = page * n
        query = {"site": site}
        fields = ["category1", "name", "form", "description", "site",
                  "priority", "categroy2", "icon"]
        projection = {field: 1 for field in fields}
        channels = list(db[COL_CHANNELS].find(query, projection=projection)
                        .skip(skip).limit(n))
        for channel in channels:
            channel["_id"] = str(channel["_id"])
        self.write({"data": channels})


class SiteChannelHandler(RequestHandler):
    @staticmethod
    def get_site_channels(site, skip=0, limit=20):
        site["id"] = str(site["_id"])
        del site["_id"]
        query = {"site": site["id"]}
        fields = ["category1", "name", "form", "description", "site",
                  "priority", "categroy2", "icon"]
        projection = {field: 1 for field in fields}
        channels = db[COL_CHANNELS].find(query, projection=projection) \
            .skip(skip).limit(limit)
        result = list()
        site_fields = {"site_%s" % k: v for k, v in site.items()}
        for channel in channels:
            c = dict(channel)
            c["id"] = str(c["_id"])
            del c["site"], c["_id"]
            c.update(site_fields)
            result.append(c)
        return result

    def get(self, *args, **kwargs):
        name = self.get_query_argument("name")
        page = int(self.get_query_argument("page", 0))
        n = int(self.get_query_argument("n", 20))
        skip = page * n
        sites = db[COL_SITES].find({"name": {"$regex": name}})
        data = list()
        for site in sites:
            data.extend(self.get_site_channels(site, skip, n))
        self.write({"data": data})


def config_logging(suffix=""):
    from logging.handlers import TimedRotatingFileHandler
    filename = "log-" + suffix + ".log"
    fileHandler = TimedRotatingFileHandler(filename=filename, when='midnight', backupCount=15)
    baseFormatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s",
                                      "%Y-%m-%d %H:%M:%S")
    fileHandler.setFormatter(baseFormatter)
    logging.getLogger().addHandler(fileHandler)
    logging.getLogger().setLevel(level=logging.INFO)


def main():
    tornado.options.parse_command_line()
    app = tornado.web.Application([
        (r"/api/wandoujia", WanDouJiaHandler),
        (r"/api/jike", JiKeHandler),
        (r"/api/weibo", WeiBoHandler),
        (r"/api/weixin", WeixinHandler),
        (r"/api/click", ClickHandler),
        (r"/sites", SiteHandler),
        (r"/channels", ChannelHandler),
        (r"/sitechannels", SiteChannelHandler),
    ])
    app.listen(9001)
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    import sys

    name = sys.argv[1]
    config_logging(name)
    if name == "weibo":
        from spiders.business.app import weibo

        weibo.main()
    elif name == "wechat":
        from spiders.business.app import wechat

        wechat.main()
    elif name == "weixin":
        from spiders.business.app import weixin

        weixin.main()
    elif name == "app":
        try:
            main()
        except Exception:
            db.client().close()
    else:
        raise ValueError("Only support weibo, weixin and app")
