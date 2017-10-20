# coding: utf-8

from bson import ObjectId
import logging
from random import randint, shuffle
import signal
import sys
from time import sleep

from spiders.business.consts import FORM_NEWS, FORM_JOKE, FORM_VIDEO, FORM_ATLAS
from spiders.business.utils import db_third_party as db
from spiders.business.utils import COL_CONFIGS, COL_CHANNELS
from spiders.business.utils import redis
from spiders.business.tasks import run_list_task
from spiders.business.tasks import run_download_task
from spiders.business.tasks import run_detail_task
from spiders.business.tasks import run_clean_filter_task
from spiders.business.tasks import run_resource_task
from spiders.business.tasks import run_prepare_task
from spiders.business.tasks import run_store_task
from spiders.business.tasks import run_video_task
from spiders.business.tasks import run_joke_task
from spiders.error import NotSupportError, MissFieldError, Error


KEY_ALL_TASK = "v1:spider:schedule:all:id"
KEY_LIST_TASK = "v1:spider:task:list:id"
KEY_DOWNLOAD_TASK = "v1:spider:task:download:id"
KEY_DETAIL_TASK = "v1:spider:task:detail:id"
KEY_CLEAN_TASK = "v1:spider:task:clean:id"
KEY_RESOURCE_TASK = "v1:spider:task:resource:id"
KEY_PREPARE_TASK = "v1:spider:task:prepare:id"
KEY_STORE_TASK = "v1:spider:task:store:id"

KEY_WEIXIN_TASK = "v1:spider:task:special:weixin:id"
KEY_BAIDU_TASK = "v1:spider:task:special:baidu:id"
KEY_HAOWAI_TASK = "v1:spider:task:special:haowai:id"
KEY_JOKE_TASK = "v1:spider:task:joke:id"
KEY_VIDEO_TASK = "v1:spider:task:video:id"


def re_distribute_task(_id):
    SITE_KEY_MAPPING = {
        "57bab42eda083a1c19957b1f": KEY_WEIXIN_TASK,
    }
    FORM_KEY_MAPPING = {
        FORM_NEWS: KEY_LIST_TASK,
        FORM_ATLAS: KEY_LIST_TASK,
        FORM_JOKE: KEY_JOKE_TASK,
        FORM_VIDEO: KEY_VIDEO_TASK,
    }
    config = db[COL_CONFIGS].find_one({"_id": ObjectId(_id)})
    channel = db[COL_CHANNELS].find_one({"_id": ObjectId(config["channel"])})
    form = channel["form"]
    site_id = str(channel["site"])
    if not channel["category1"]:
        return
    if site_id in SITE_KEY_MAPPING:
        redis.sadd(SITE_KEY_MAPPING[site_id], _id)
    elif form in FORM_KEY_MAPPING:
        redis.sadd(FORM_KEY_MAPPING[form], _id)
    else:
        raise ValueError("Not support form: %s, id: %s" % (form, _id))


LONG_TIME_MAPPING = {
    KEY_RESOURCE_TASK: (run_resource_task, KEY_PREPARE_TASK),
}
MIDDLE_TIME_MAPPING = {
    KEY_LIST_TASK: (run_list_task, KEY_DOWNLOAD_TASK),
    KEY_DOWNLOAD_TASK: (run_download_task, KEY_DETAIL_TASK),
    KEY_VIDEO_TASK: (run_video_task, KEY_CLEAN_TASK),
    KEY_JOKE_TASK: (run_joke_task, KEY_CLEAN_TASK),
}
SHORT_TIME_MAPPING = {
    KEY_ALL_TASK: (re_distribute_task, None),
    KEY_DETAIL_TASK: (run_detail_task, KEY_CLEAN_TASK),
    KEY_CLEAN_TASK: (run_clean_filter_task, KEY_RESOURCE_TASK),
    KEY_PREPARE_TASK: (run_prepare_task, KEY_STORE_TASK),
    KEY_STORE_TASK: (run_store_task, None)
}


def service(mapping):

    should_be_kill = list()

    def handle_kill_signals(sig, frame):
        if not should_be_kill:
            should_be_kill.append(sig)

    def spop(keys):
        shuffle(keys)
        while 1:
            for key in keys:
                if should_be_kill:
                    sys.exit(0)
                _id = redis.spop(key)
                if _id:
                    return key, _id
            sleep(randint(3, 8))

    signal.signal(signal.SIGTERM, handle_kill_signals)
    signal.signal(signal.SIGINT, handle_kill_signals)
    while 1:
        key, _id = spop(keys=mapping.keys())
        logging.info("From [%s] get [%s]" % (key, _id))
        runner, next_key = mapping[key]
        try:
            id = runner(_id)
        except NotSupportError as e:
            logging.error(str(e.message) + "$id:" + _id)  # Todo record not support domain
        except MissFieldError as e:
            logging.warning(str(e.message) + "$id:" + _id)
        except Error as e:
            logging.error(str(e.message) + "$id:" + _id, exc_info=True)
        except Exception as e:
            logging.error(str(e.message) + "$id:" + _id, exc_info=True)
        else:
            if not next_key:
                continue
            if not id:
                continue
            if isinstance(id, list):
                redis.sadd(next_key, *id)
            elif id:
                redis.sadd(next_key, id)
            else:
                pass


def config_logging(suffix=""):
    from logging.handlers import TimedRotatingFileHandler, DatagramHandler
    base_format = logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%Y-%m-%d %H:%M:%S")
    filename = "log-" + suffix + ".log"
    file_handler = TimedRotatingFileHandler(filename=filename, when='midnight', backupCount=15)
    file_handler.setFormatter(base_format)
    logging.getLogger().addHandler(file_handler)
    udp_handler = DatagramHandler(host="10.47.54.115", port=10000)  # 设置 udp 服务器地址
    udp_handler.setFormatter(base_format)
    udp_handler.setLevel(level=logging.ERROR)
    logging.getLogger().addHandler(udp_handler)
    logging.getLogger().setLevel(level=logging.INFO)


if __name__ == "__main__":
    t = sys.argv[1].lower()
    config_logging(t)
    if t == "long":
        service(LONG_TIME_MAPPING)
    elif t == "short":
        service(SHORT_TIME_MAPPING)
    elif t == "middle":
        service(MIDDLE_TIME_MAPPING)
    else:
        raise ValueError("Only support long, middle, short command params")
