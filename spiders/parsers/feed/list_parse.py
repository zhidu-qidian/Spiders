# coding:utf-8

"""
列表页解析, 返回空列表或 list of models.Fields.to_dict()

解析配置文件为 json 格式, 包含 domain, list 两个字段
- domain: str 要解析的网站域名
- list: array 域名下的所有解析配置

用 HtmlTag 表示 html 抽取配置格式; JsonItem 表示 json 抽取配置格式

HtmlTag 说明:
- method: str bs4 支持的定位 tag 的函数[find, find_all, select]
- params: dict 上面的 method 的参数
- attribute: str,可选 要抽取的属性, 默认为 text
JsonItem 说明:
直接用 | 分隔的字符串定位

解析配置说明:
- publish_time: HtmlTag or JsonItem or null, 新闻发布时间
- title: HtmlTag or JsonItem or null, 新闻标题
- url: HtmlTag or JsonItem or str, 新闻链接地址, str 表示 url 模板, 配合 fields 字
  段生成 url 链接
- abstract: HtmlTag or JsonItem or null, 新闻摘要
- author: HtmlTag or JsonItem or null, 新闻作者
- thumb: HtmlTag or JsonItem or null, 新闻列表页图片
- publish_site: HtmlTag or JsonItem or null, 新闻发布源
- keywords: HtmlTag or JsonItem or null, 新闻的标签
- comment_id: HtmlTag or JsonItem or null, 评论需要的id
- fields: array of string 配合 url 字段中的模板使用
- list: HtmlTag or JsonItem, 定位新闻列表
- skip: array of 2 int,可选 解析 http response body 前要截取的字符位置, json 解析用
  [1, -1] 表示截取第1个字符到最后一个字符(不包含最后一个字符)
- filter: str, 过滤掉 url 中包含该字符串的数据
- type: str,可选 ajax or html 表示是 html 配置还是 json 配置, 默认 html
- crawler: str, 该配置的名称, 使用列表页解析需要该名称
"""

import os
import json
import re
from types import ListType, StringTypes, IntType
from urlparse import urljoin
from bs4 import BeautifulSoup

from .utils import get_path_files, clean_date_time, get_dict_value
from .htmltools import find_tags
from .htmltools import get_tag_attribute
from .specials import special_mapping
from .models import Fields


def load_config_files(directory="configs"):
    """ 加载当前目录下 directory 文件夹中的 json 配置文件(只加载以 '.json' 结尾的) """
    prefix = os.path.split(os.path.abspath(__file__))[0]
    path = os.sep.join([prefix, directory])
    files = get_path_files(path)
    configs = dict()
    for f in files:
        config = load_file_configs(f)
        configs.update(config)
    return configs


def load_file_configs(filepath):
    """ 加载指定文件中的所有配置项 """
    with open(filepath) as f:
        obj = json.load(f)
    configs = dict()
    for item in obj["list"]:
        config = load_config_item(item)
        configs.update(config)
    return configs


def load_config_item(item):
    """ 加载配置项, 生成配置字典 """
    assert isinstance(item, dict)
    config = dict()
    name = item["crawler"]
    del item["crawler"]
    config[name] = {k: v for k, v in item.items() if v is not None}
    config[name]["type"] = item.get("type", "html")  # 默认 html 解析
    return config


class ListParser(object):

    def __init__(self):
        """ 初始加载配置 """
        self.configs = load_config_files()

    def update_confs(self):
        """ 更新配置 """
        self.configs = load_config_files()

    def __call__(self, document, crawler, url=None):
        """ 列表页解析主函数，对外开放的接口

        :param document: str or unicode, 要解析的文档
        :param crawler: str, 解析器名称
        :param url: str, 文档的链接
        :return: list of models.Fields.to_dict()
        """
        if crawler in special_mapping:  # 特殊列表页解析
            return special_mapping[crawler](document, url)
        if crawler not in self.configs:  # 不支持的 crawler
            return list()
        config = self.configs[crawler]
        if config["type"] == "ajax":
            items = self._parse_list_ajax(document, config)
        else:
            items = self._parse_list_html(document, config)
        result = list()
        for item in items:
            if not item.is_valid():
                continue
            if config.get("filter") and re.search(config["filter"], item.url):
                continue
            if item.publish_time:
                if not isinstance(item.publish_time, StringTypes):
                    item.publish_time = str(item.publish_time)
                item.publish_time = clean_date_time(item.publish_time)
            if url:
                item.url = urljoin(url, item.url)
                if item.thumb:
                    item.thumb = urljoin(url, item.thumb)
            # baijiahao url 需转成 baijia
            _baijiaurl = "http://baijiahao.baidu.com"
            if item.url.startswith(_baijiaurl):
                item.url = item.url.replace(_baijiaurl, "https://baijia.baidu.com")
            result.append(item.to_dict())
        return result

    @staticmethod
    def _parse_list_ajax(document, config):
        """ 解析 JSON 形式的列表页

        :param document: str or unicode, 要解析的文档
        :param config: dict, 解析配置
        :return: list of models.Fields
        """
        list_params = config.get("list")
        if "skip" in config and config["skip"]:
            start, end = config["skip"]
            document = document.strip()[start: end]
        try:
            data = json.loads(document)
        except Exception as e:
            from utils import parse_js
            data = parse_js(document)
        items = list()
        if list_params is None or isinstance(data, ListType):
            element_list = data
        elif isinstance(list_params, IntType):
            for num, key in enumerate(data):
                if isinstance(data[key], ListType):
                    element_list = data[key]
                    break
            else:
                element_list = list()
        else:
            element_list = get_dict_value(data, list_params)
        if not element_list:
            return items
        for i in element_list:
            item = {k: get_dict_value(i, v) for k, v in config.items()
                    if k in Fields.names and k != "url"}
            if config.get("fields"):  # url 模板需配合 fields 配置生成
                fields = [get_dict_value(i, k) for k in config.get("fields")]
                item["url"] = config["url"].format(*fields)
            else:
                item["url"] = get_dict_value(i, config["url"])
            if isinstance(item.get("keywords", ""), list):
                item["keywords"] = ";".join(item["keywords"])
            items.append(Fields.from_dict(item))
        return items

    def _parse_list_html(self, document, config):
        """ 解析HTML形式的列表页

        :param document: str, 要解析的文档
        :param config: dict, 解析配置
        :return: list of models.Fields
        """
        list_params = config["list"]
        document = self._clean_html(document)
        encoding = None if isinstance(document, unicode) else "utf8"
        soup = BeautifulSoup(document, "lxml", from_encoding=encoding)
        tags = find_tags(soup, param=list_params)
        items = list()
        for tag in tags:
            item = dict()
            for k, v in config.items():
                if k in Fields.names:
                    attribute = v.get("attribute", "text")
                    item[k] = get_tag_attribute(tag, v, attribute=attribute)
            items.append(Fields.from_dict(item))
        return items

    @staticmethod
    def _clean_html(document):
        if document.startswith("<?xml"):
            index = document.index(">")
            return document.replace(document[:index+1], "")
        return document
