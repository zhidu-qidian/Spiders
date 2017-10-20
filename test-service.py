# coding

import logging

from bson import ObjectId
from tornado.web import RequestHandler
import tornado.web
import tornado.ioloop
import tornado.httpserver
import tornado.options
from pymongo.errors import DuplicateKeyError

from spiders.business.tasks import run_list_task, run_video_task, run_joke_task
from spiders.alioss import TestObjectUploader
from spiders.images import process_image_response
from spiders.utilities import http
from spiders.parsers import PageParser, DetailParser, FeedParser
from spiders.business.utils import db_third_party as db
from spiders.business.utils import COL_CONFIGS, COL_CHANNELS, COL_ADVERTISEMENT


class ListParseHandler(RequestHandler):

    def post(self, *args, **kwargs):
        _id = self.get_body_argument("id", "")
        if _id:
            config = db[COL_CONFIGS].find_one({"_id": ObjectId(_id)})
            channel = db[COL_CHANNELS].find_one({"_id": ObjectId(config["channel"])})
            form = channel["form"]
            if form == "news" or form == "atlas":
                result = run_list_task(_id=_id, debug=True)
            elif form == "joke":
                result = run_joke_task(_id, debug=True)
            elif form == "video":
                result = run_video_task(_id, debug=True)
            else:
                result = "Not support form %s" % form
        else:
            url = self.get_body_argument("url")
            crawler = self.get_body_argument("crawler")
            _url, content = http.stable_download_content(url)
            result = FeedParser(document=content, crawler=crawler, url=url)
        self.write({"data": result})


class PageParseHandler(RequestHandler):

    def post(self, *args, **kwargs):
        url = self.get_body_argument("url")
        _url, content = http.stable_download_content(url)
        urls = PageParser(document=content, url=_url)
        self.write({"data": urls})


class DetailParseHandler(RequestHandler):

    def post(self, *args, **kwargs):
        url = self.get_body_argument("url")
        _url, content = http.stable_download_content(url)
        result = DetailParser(url=url, document=content)
        self.write(result)


class AdvertisementHandler(RequestHandler):

    def post(self, *args, **kwargs):
        url = self.get_body_argument("url")
        refer = self.get_body_argument("refer", None)
        md5 = self.get_body_argument("md5", None)
        if md5 and len(md5) == 32:
            document = {"url": url, "referer": refer, "online": True, "md5": md5}
            try:
                db[COL_ADVERTISEMENT].insert_one(document)
            except DuplicateKeyError:
                pass
            self.write({"code": 200})
        else:
            req = http.Request(url=url, headers={"referer": refer})
            r = http.download(req)
            images = process_image_response(r, TestObjectUploader)
            if not images:
                images = dict()
            self.write(images)


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
    config_logging("test")
    app = tornado.web.Application([
        (r"/test/parse/list", ListParseHandler),
        (r"/test/parse/page", PageParseHandler),
        (r"/test/parse/detail", DetailParseHandler),
        (r"/test/advertisement", AdvertisementHandler),
    ])
    app.listen(9002)
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()
