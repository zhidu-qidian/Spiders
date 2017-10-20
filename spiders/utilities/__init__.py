# coding: utf-8

""" 公共模块 """

from datetime import datetime
import functools
import hashlib
from HTMLParser import HTMLParser
import re
from urllib import urlencode
from urlparse import urlparse, parse_qs, urlunparse

from bs4 import BeautifulSoup


def to_unicode(string):
    assert isinstance(string, (str, unicode))
    if isinstance(string, str):
        return string.decode("utf-8")


def ToUnicode(func):

    @functools.wraps(func)
    def wrapper(string):
        if isinstance(string, str):
            string = string.decode("utf-8")
        return func(string)
    return wrapper


_html_parser = HTMLParser()


@ToUnicode
def normalize_punctuation(string):
    pairs = [(u'\xa0', u' ')]  # 要转换的标点对儿
    for src, dst in pairs:
        string = string.replace(src, dst)
    return string


@ToUnicode
def html_un_escape(string):
    return _html_parser.unescape(string)


def extract_text_from_html(string):
    soup = BeautifulSoup(string, "html.parser")
    return soup.text


@ToUnicode
def get_string_md5(string):
    string = string.encode("utf-8")
    return hashlib.md5(string).hexdigest()


def url_encode_params(params):
    for k, v in params.items():
        if isinstance(v, (str, unicode, int)):
            params[k] = [v]
    for k, v in params.items():
        for i, _v in enumerate(v):
            if isinstance(_v, unicode):
                v[i] = _v.encode("utf-8")
        params[k] = v
    return urlencode(params, doseq=True)


def rebuild_url(url, params):
    for k, v in params.items():
        if isinstance(v, (str, unicode, int)):
            params[k] = [v]
    result = urlparse(url)
    query = parse_qs(result.query)
    query.update(params)
    for k, v in query.items():
        for i, _v in enumerate(v):
            if isinstance(_v, unicode):
                v[i] = _v.encode("utf-8")
        query[k] = v
    new = list(result)
    new[4] = urlencode(query, doseq=True)
    return urlunparse(tuple(new))


def remove_url_query_params(url):
    """ 移除 url 中的 query 参数, 只保留 ? 之前的部分"""
    new = list(urlparse(url))
    new[4] = new[5] = ""
    return urlunparse(tuple(new))


def format_datetime_string(d):
    """ 归一化时间字符串 "%Y-%m-%d %H:%M:%S" or ""
    
    :param d: 要计算的原始数据(时间戳或字符串)
    :type d: int, float, str
    :return: 返回统一格式的时间数据或空
    :rtype: str
    """
    dt = ""
    if not d:
        return dt
    if isinstance(d, (int, float)) or d.isdigit():
        timestamp = int(d)
        if len(str(timestamp)) == 13:
            timestamp /= 1000
        try:
            dt = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass
    else:
        dt = clean_date_time(d)
    return dt


def utc_datetime_now():
    return datetime.utcnow()


def clean_date_time(string):
    """清洗时间

    :param string: 包含要清洗时间的字符串
    :type string: str
    :return: 生成的字符串, 格式为 2016-02-01 12:01:59
    :rtype: str
    """
    if isinstance(string, str):
        string = string.decode("utf-8")
    date_time_string = ""
    if string.isdigit():
        length = len(string)
        timestamp = int(string)
        if length == 13:
            timestamp /= 1000
            length -= 3
        if length == 10:
            date_time = datetime.fromtimestamp(timestamp)
            return date_time.strftime("%Y-%m-%d %H:%M:%S")
    p_date_list = [
        u"((20\d{2})[/\.-])(\d{1,2})[/\.-](\d{1,2})",
        u"((20\d{2})年)(\d{1,2})月(\d{1,2})",
        u"((\d{2})[/\.-])(\d{1,2})[/\.-](\d{1,2})",
        u"((20\d{2})[/\.-])?(\d{1,2})[/\.-](\d{1,2})",
        u"((20\d{2})年)?(\d{1,2})月(\d{1,2})",
    ]
    for p_date in p_date_list:
        date_match = re.search(p_date, string)
        if date_match is not None:
            break
    else:
        return date_time_string
    p_time = r"(\d{1,2}):(\d{1,2})(:(\d{1,2}))?"
    time_match = re.search(p_time, string)
    now = datetime.now()
    year_now = now.strftime("%Y")
    hour_now = now.strftime("%H")
    minute_now = now.strftime("%M")
    second_now = now.strftime("%S")
    if date_match is None:
        return date_time_string
    else:
        date_groups = date_match.groups()
    if time_match is None:
        time_groups = (hour_now, minute_now, ":" + second_now, second_now)
    else:
        time_groups = time_match.groups()
    year = date_groups[1]
    month = date_groups[2]
    if len(month) == 1:
        month = "0" + month
    day = date_groups[3]
    if len(day) == 1:
        day = "0" + day
    hour = time_groups[0]
    minute = time_groups[1]
    second = time_groups[3]
    if year is None:
        year = year_now
    if second is None:
        second = second_now
    if len(year) == 2:
        year = "20" + year
    date_string = "-".join([year, month, day])
    time_string = ":".join([hour, minute, second])
    date_time_string = date_string + " " + time_string
    return date_time_string
