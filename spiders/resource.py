# coding: utf-8

from urllib import quote

from pymongo import MongoClient
from redis import from_url

from settings import MONGODB_HOST_PORT, MONGODB_PASSWORD
from settings import REDIS_URL, REDIS_MAX_CONNECTIONS


def get_mongodb_database(database, user="third"):
    url = "mongodb://{0}:{1}@{2}/{3}".format(
        user, quote(MONGODB_PASSWORD), MONGODB_HOST_PORT, database
    )
    client = MongoClient(host=url, maxPoolSize=1, minPoolSize=1)
    return client.get_default_database()


def get_cache_client(db):
    return from_url(REDIS_URL, db=db, max_connections=REDIS_MAX_CONNECTIONS)
