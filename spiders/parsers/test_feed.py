# coding: utf-8

"""
列表页解析测试
"""

import os
import sys

import chardet
from w3lib.encoding import html_to_unicode
import requests

from feed.list_parse import ListParser


def format_detail(article):
    """格式化详情"""

    def _get_attributes(tag):
        _attributes = ""
        for key, value in tag.items():
            if key in ["tag", "text"]:
                continue
            else:
                _attributes += " {key}='{value}' ".format(key=key, value=value)
        return _attributes

    strings = list()
    strings.append("title: %s" % article.get("title"))
    strings.append("publish time: %s" % article.get("date"))
    strings.append("publish site: %s" % article.get("source"))
    strings.append("content:")
    for item in article["content"]:
        attributes = _get_attributes(item)
        if item["tag"] == "p":
            strings.append(u"<p>{text}</p>".format(text=item.get("text")))
        elif item["tag"] == "img":
            strings.append(u"<img{}>".format(attributes))
        else:
            text = item.get("text")
            if not text:
                text = ""
            strings.append(u"<{0}{1}>{2}</{0}>".format(item["tag"], attributes, text))
    return os.linesep.join(strings)


def display_detail(article):
    """显示解析详情"""
    print "*" * 80
    print format_detail(article)


def format_list(items):
    """解析结果格式化"""
    filter_keys = {"title", "url"}
    strings = list()
    strings.append("length: %s" % len(items))
    for item in items:
        other = ""
        for key, value in item.items():
            if key not in filter_keys and value:
                other += u", {key}: {value}".format(key=key, value=value)
        strings.append("url: %s title: %s %s" % (item.get("url"), item.get("title"), other))
    return os.linesep.join(strings)


def display_list(items):
    """显示解析列表"""
    print "*" * 80
    print format_list(items)


def stable_download_content(url):
    headers = {"user-agent": "Mozilla/5.0 (X11; Linux x86_64) "
                             "AppleWebKit/537.36 (KHTML, like Gecko) "
                             "Chrome/57.0.2987.133 Safari/537.36"}
    r = requests.get(url, headers=headers, timeout=(10, 30))
    _, content = html_to_unicode(
        content_type_header=r.headers.get("Content-Type"),
        html_body_str=r.content,
        auto_detect_fun=lambda x: chardet.detect(x).get("encoding")
    )
    return r.url, content


def main(url, crawler):
    """测试主函数"""
    _url, content = stable_download_content(url)
    parser = ListParser()
    items = parser(content, crawler, _url)

    # print items
    display_list(items)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
