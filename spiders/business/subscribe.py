# coding: utf-8

import json

from utils import redis

__author__ = "lixianyang"
__email__ = "705834854@qq.com"
__date__ = "2017-06-01 17:09"


# 奇点资讯订阅所有数据

def qdzx(data):
    STORE_CACHE_KEY = "v1:store:qdzx"
    redis.lpush(STORE_CACHE_KEY, json.dumps(data))
