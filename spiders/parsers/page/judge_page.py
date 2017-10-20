# coding: utf-8

""" 翻页判断服务 """

import re
import os
from urlparse import urljoin
from urlparse import urlparse
from bs4 import BeautifulSoup
from htmltool import find_tag
from htmltool import find_tags
from htmltool import extract_tag_attribute
from utils import get_path_files
from utils import load_json_file
import logging

_logger = logging.getLogger(__name__)


class JudgePage(object):
    """
    翻页解析/判断类别
    """

    def __init__(self):
        """初始加载配置"""
        self.configs = self._load_confs()

    def _load_confs(self):
        """
        加载配置
        :return: 配置字典 {key：domain，value：config}
        """
        prefix = os.path.split(os.path.abspath(__file__))[0]
        path = os.sep.join([prefix, "configs"])
        files = get_path_files(path)
        config = dict()

        for f in files:
            obj = load_json_file(f)
            domain = obj["domain"]
            config[domain] = obj["conf"]
        return config

    def update_configs(self):
        """重新加载配置进行更新"""
        self.configs = self._load_confs()

    def _get_tag_number(self, root, attri=None):
        """寻找标签数字"""
        if root is None:
            return 0
        if not attri: attri = "text"
        text = extract_tag_attribute(root, attri)
        text = text[::-1]
        pattern = "[^0-9]*([0-9]+)"
        match = re.search(pattern, text)
        if match is None:
            return 0
        return int(match.group(1)[::-1])

    def _get_page_number(self, document, param):
        """根据页面内容和参数找到页面数"""
        if not param:
            return 0
        encoding = None if isinstance(document, unicode) else "utf8"
        root = BeautifulSoup(document, "lxml", from_encoding=encoding)
        number = 0
        attri = param.get("attribute")
        if param.get("type"):
            _type = param["type"]
            tags = find_tags(root, param)
            if _type == "sum":
                return len(tags)
            elif _type == "last":
                for tag in tags[::-1]:
                    number = self._get_tag_number(tag, attri)
                    if number > 0:
                        break
            return number
        tag = find_tag(root, param)
        return self._get_tag_number(tag, attri)

    def _get_page_urls(self, url, number, start, template):
        """获取页面地址"""
        if start is None:
            start = 2
        urls = []
        tmp = template["template"]
        separator = template.get("separator", ".")
        if template["join"]:
            for page in range(start, number + 1):
                urls.append(urljoin(url, tmp % page))
        else:
            for page in range(start, number + 1):
                if separator:
                    s = url.rindex(separator)
                    prefix = url[:s]
                else:
                    prefix = url
                tail = tmp % page
                urls.append(prefix + tail)
        num_delete = template.get("minus", 0)
        if num_delete > len(urls):
            num_delete = len(urls)
        urls = urls[:len(urls) - num_delete]
        return urls

    def __call__(self, document, url):
        """
        解析页面翻页
        :param document:文档内容
        :param url: 文档url
        :return: url列表
        """
        domain = urlparse(url).netloc
        for key, value in self.configs.items():
            if domain.endswith(key):
                k = key
                break
        else:
            return list()
        number_param = self.configs[k]["NUMBER"]
        document = self.html_clean(document)
        number = self._get_page_number(document, number_param)
        if number == 0:
            return list()
        if number >= 200:
            number = 200
        urls = self._get_page_urls(url, number, self.configs[k]["START"],
                                   self.configs[k]["TEMPLATE"])
        return urls

    def html_clean(self, document):
        if document.startswith("<?xml"):
            index = document.index(">")
            document = document.replace(document[:index + 1], "")
        return document
