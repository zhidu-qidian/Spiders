# coding: utf-8

""" 爬虫所有业务逻辑模块 """


class Worker(object):

    @classmethod
    def run(cls):
        raise NotImplementedError


class DownloadWorker(Worker):

    @classmethod
    def run(cls):
        pass
