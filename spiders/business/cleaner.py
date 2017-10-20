# coding: utf-8

from ..utilities import html_un_escape
from ..utilities import normalize_punctuation
from ..utilities import extract_text_from_html

__author__ = "lixianyang"
__email__ = "705834854@qq.com"
__date__ = "2017-05-12 17:02"


class Cleaner(object):

    @classmethod
    def clean_title(cls, title):
        string = html_un_escape(title)
        string = normalize_punctuation(string)
        return string.strip()


class NewsCleaner(Cleaner):

    @classmethod
    def clean_content(cls, content):
        for i, item in enumerate(content):
            if item["tag"] == "p":
                content[i]["text"] = html_un_escape(item["text"])
        return content


class VideoCleaner(Cleaner):

    @classmethod
    def run(cls, *args, **kwargs):
        pass

    @classmethod
    def clean_title(cls, title):
        return title


class JokeCleaner(Cleaner):

    @classmethod
    def run(cls, *args, **kwargs):
        pass


def is_news_valid(news):
    if len(news["title"]) <= 7:
        return False
    content = news["content"]
    if len(content) > 3:
        return True
    for item in content:
        if item["tag"] == "p":
            if len(extract_text_from_html(item["text"])) > 30:
                return True
        elif item["tag"] == "img":
            if item["src"] is None:
                continue
            else:
                return True
        else:
            return True
    return False


