# coding: utf-8

from datetime import datetime
import logging

from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from spiders.models import VideoFields
from spiders.business.utils import db_third_party as db
from spiders.business.utils import COL_REQUESTS
from spiders.business.utils import redis

import requests

__author__ = "lixianyang"
__email__ = "705834854@qq.com"
__date__ = "2017-05-11 14:25"


KEY_CLEAN_TASK = "v1:spider:task:clean:id"
KEY_DOWNLOAD_TASK = "v1:spider:task:download:id"


def to_unicode(string):
    if isinstance(string, str):
        return string.decode("utf-8")
    return string


class WeiBoProcessor(object):

    @classmethod
    def get_weibo_from_id(cls, _id):
        wb = db["weibo"].find_one({"_id": ObjectId(_id)})
        return wb

    @classmethod
    def process_video(cls, wb):
        """处理微博视频，目前只处理秒拍的视频，其他的过滤掉"""
        video = wb["video"]
        if video.get("streamUrlHd"):
            url = video["streamUrlHd"]
        else:
            url = video["streamUrl"]
        if not url or not url.startswith("http://gslb.miaopai.com"):  # 只处理秒拍视频
            logging.warning("Can't support: %s" % url)
            return
        thumbnail = wb["video"]["pagePic"]
        if not thumbnail.startswith("http"):
            logging.info("Invalid thumbnail: %s" % thumbnail)
            return
        f = "%a %b %d %H:%M:%S +0800 %Y"
        publish_time = datetime.strptime(wb["status"]["createDate"], f)
        duration = int(wb["video"].get("duration", 0))
        clicks = int(wb["video"].get("onlineUsersNumber", 0))
        likes = int(wb["status"].get("attitudesCount", 0))
        publish_name = u"微博热点"
        site_icon = "https://oss-cn-hangzhou.aliyuncs.com/bdp-images/" \
                    "35731635d18811e6bfb780e65007a6da.jpg"
        if "avatarHd" in wb["status"]:
            site_icon = wb["status"]["avatarHd"]
            publish_name = wb["status"]["userName"]
        assert isinstance(publish_time, datetime)
        video = VideoFields()
        video.title = wb["status"]["blogContent"]
        video.src = url
        video.thumbnail = thumbnail
        video.duration = duration
        video.n_read = clicks
        video.n_like = likes
        video.publish_time = publish_time.strftime("%Y-%m-%d %H:%M:%S")
        video.publish_ori_name = publish_name
        video.publish_ori_icon = site_icon
        video.publish_ori_url = wb["video"]["h5Url"]
        video.tags = ";".join(wb.get("toptitle", []))
        doc = dict()
        doc["channel"] = "5938c12e921e6d313692ccc8"
        doc["config"] = "5938c12e921e6d313692ccc9"
        doc["form"] = "video"
        doc["site"] = "57ac3802da083a1c19957b1b"
        doc["time"] = datetime.utcnow()
        doc["fields"] = video.to_dict()
        doc["unique"] = video.publish_ori_url
        doc["procedure"] = 20000  # 完成详情页解析状态
        _id = cls.store_request(doc)
        if _id:
            logging.info("process weibo video %s" % _id)
            redis.sadd(KEY_CLEAN_TASK, _id)

    @classmethod
    def process_news(cls, wb):
        """处理不包含视频的微博"""
        if not wb.get("mblogcards"):
            return "Miss outer link in blog content"
        short_url = wb["mblogcards"][0]["shortUrl"]
        try:
            r = requests.get(short_url, timeout=(5, 15))
        except Exception as e:
            logging.warning(e.message)
            return
        url = r.url
        doc = dict()
        doc["channel"] = "5938c106921e6d313692ccc6"
        doc["config"] = "5938c106921e6d313692ccc7"
        doc["form"] = "news"
        doc["site"] = "57ac3802da083a1c19957b1b"
        doc["time"] = datetime.utcnow()
        doc["fields"] = dict()
        doc["list_fields"] = {"url": url}
        doc["unique"] = url
        doc["pages"] = [{"url": url, "html": ""}]
        doc["procedure"] = 0  # 完成列表页解析状态
        _id = cls.store_request(doc)
        if _id:
            logging.info("process weibo news %s" % _id)
            redis.sadd(KEY_DOWNLOAD_TASK, _id)

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

    @classmethod
    def has_video(cls, wb):
        """判断该条微博是否包含视频"""
        return True if "video" in wb else False

    @classmethod
    def process_hot_news(cls, wb):
        blog = wb.get("mblogcards")
        if not blog:
            logging.warning("Hot news miss mblogcards: %s" % str(wb["_id"]))
            return
        title = blog[0]["urlTitle"]
        title = to_unicode(title)
        if len(title) < 10:
            logging.warning("Hot news too short title: %s" % title)
        else:
            logging.info("Hot news title: %s" % title)
            url = "http://bdp.deeporiginalx.com/v2/hot/crawler/news"
            data = {"news": [title]}
            try:
                r = requests.post(url, data=data, timeout=(5, 10))
            except Exception as e:
                logging.error(e.message)
            else:
                logging.info(r.content)

    @classmethod
    def process(cls, _id):
        """处理微博：微博视频，微博，热点新闻"""
        wb = cls.get_weibo_from_id(_id)
        if cls.has_video(wb):
            cls.process_video(wb)
        else:
            cls.process_news(wb)
        if not cls.has_video(wb):
            cls.process_hot_news(wb)


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
    key = "v1:weibo:process"
    while 1:
        _, _id = redis.brpop(key)
        logging.info("Start process: %s" % _id)
        try:
            WeiBoProcessor.process(_id)
        except Exception as e:
            logging.error(e.message)
        logging.info("End process: %s" % _id)


if __name__ == "__main__":
    config_logging("weibo")
    main()
