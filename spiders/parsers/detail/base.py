# coding: utf-8

"""基础类"""

import json
import types

from bs4 import BeautifulSoup
from lxml import html
from lxml.html.clean import Cleaner
from utils import clean_date_time
from html import absolute_links
from html import extract_tag_attribute
from html import find_tag, find_tags
from html import unescape

__author__ = "Sven Lee"
__copyright__ = "Copyright 2016-2019, ShangHai Lie Ying"
__credits__ = ["Sven Lee"]
__license__ = "Private"
__version__ = "1.0.0"
__email__ = "lee1300394324@gmail.com"
__date__ = "2016-07-15 16:08"


class ExtractorInterface(object):
    """抽取基类"""

    def extract_title(self, param):
        raise NotImplementedError

    def extract_date(self, param):
        raise NotImplementedError

    def extract_source(self, param):
        raise NotImplementedError

    def extract_author(self, param):
        raise NotImplementedError

    def extract_editor(self, param):
        raise NotImplementedError

    def extract_summary(self, param):
        raise NotImplementedError

    def extract_tags(self, param):
        raise NotImplementedError

    def extract_content(self, param, **kwargs):
        raise NotImplementedError


class BaseCleaner(Cleaner):
    scripts = True
    javascript = True
    comments = True
    style = True
    links = True
    meta = False
    page_structure = False
    processing_instructions = True
    embedded = False
    frames = False
    forms = False
    annoying_tags = False
    remove_unknown_tags = False
    safe_attrs_only = False
    add_nofollow = False


class BaseExtractor(ExtractorInterface):
    base_cleaner_cls = BaseCleaner
    cleaner_cls = None
    parser_cls = None

    def __init__(self, document, url=None, encoding="utf-8"):
        self.origin = document
        self.url = url
        if isinstance(document, unicode):
            encoding = None
        self.html = self.html_clean(self.origin, cleaner=self.base_cleaner_cls, encoding=encoding)
        self._html = self.html_clean(self.html, cleaner=self.cleaner_cls, encoding=encoding)
        self.soup = BeautifulSoup(self.html, "lxml", from_encoding=encoding)
        self._soup = BeautifulSoup(self._html, "lxml", from_encoding=encoding)
        absolute_links(self._soup, self.url)
        self.after_init()

    def after_init(self):
        pass

    @staticmethod
    def html_clean(document, cleaner, encoding="utf-8"):
        assert issubclass(cleaner, Cleaner)
        instance = cleaner()
        parser = html.HTMLParser(
            encoding=encoding,
            remove_comments=True,
            remove_blank_text=True,
            remove_pis=True,
        )
        root = html.document_fromstring(document, parser=parser)
        root = instance.clean_html(root)
        return html.tostring(root)

    @staticmethod
    def _extract_tag(root, param):
        """
        param = {
            "method": "find_all",
            "params": {},
            "nth": 0,
            "attribute": "text",
        }
        :param root:
        :type root:
        :param param:
        :type param:
        :return:
        :rtype:
        """
        tag = find_tag(root, param)
        attribute = param.get("attribute")
        if attribute is None:
            string = extract_tag_attribute(tag, "text")
        else:
            string = extract_tag_attribute(tag, attribute)
        return string

    def judge_missing(self, param):
        if param is None:
            return False
        if isinstance(param, list):
            for p in param:
                if find_tag(self.soup, p):
                    return True
        else:
            if find_tag(self.soup, param):
                return True
        return False

    def extract_title(self, param):
        if param is None:
            return self._extract_title()
        title = self._extract_tag(self.soup, param)
        return unescape(self.clean_title(title))

    def clean_title(self, title):
        return title

    def _extract_title(self):
        return ""

    def extract_date(self, param):
        datetime = ""
        if param is None:
            datetime = self._extract_date()
        elif isinstance(param, dict):
            datetime = self._extract_tag(self.soup, param)
        else:
            for p in param:
                datetime = self._extract_tag(self.soup, p)
                if datetime:
                    break
        return self.clean_date(datetime)

    def clean_date(self, datetime):
        return clean_date_time(datetime)

    def _extract_date(self):
        return ""

    def extract_source(self, param):
        if param is None:
            return self._extract_source()
        if isinstance(param, (types.StringType, types.UnicodeType)):
            return param
        source = ""
        if isinstance(param, dict):
            source = self._extract_tag(self.soup, param)
        else:
            for p in param:
                source = self._extract_tag(self.soup, p)
                if source:
                    break
        return unescape(self.clean_source(source))

    def clean_source(self, source):
        return source

    def _extract_source(self):
        return ""

    def extract_author(self, param):
        if param is None:
            return self._extract_author()
        author = self._extract_tag(self.soup, param)
        return unescape(self.clean_author(author))

    def clean_author(self, author):
        return author

    def _extract_author(self):
        return ""

    def extract_editor(self, param):
        if param is None:
            return self._extract_editor()
        editor = self._extract_tag(self.soup, param)
        return unescape(self.clean_author(editor))

    def clean_editor(self, editor):
        return editor

    def _extract_editor(self):
        return ""

    def extract_summary(self, param):
        if param is None:
            return self._extract_summary()
        summary = self._extract_tag(self.soup, param)
        return unescape(self.clean_summary(summary))

    def clean_summary(self, summary):
        return summary

    def _extract_summary(self):
        return ""

    def extract_tags(self, param):
        if param is None:
            return self._extract_tags()
        tags = self._extract_tag(self.soup, param)
        return unescape(self.clean_tags(tags))

    def clean_tags(self, tags):
        return tags

    def _extract_tags(self):
        return ""

    def extract_content(self, param, clean=None, before=None, after=None):
        roots = list()
        if param is None:
            roots.append(self._find_content_tag())
        elif isinstance(param, list):  # fixme: 找到的节点之间有包含关系
            for p in param:
                root = find_tag(self._soup, p)
                if root is None or root in roots:
                    continue
                else:
                    roots.append(root)
        else:
            roots.append(find_tag(self._soup, param))
        content = list()
        for root in roots:
            if root is None:
                continue
            if before is not None:
                self._clean_content_before(root, before)
            if after is not None:
                self._clean_content_after(root, after)
            if clean is not None:
                self._clean_content(root, clean)
            content.extend(self.parse_content(root))
        return self.clean_content(content)

    def clean_content(self, content):
        return content

    def _clean_content(self, root, params):
        if isinstance(params, dict):
            params = [params]
        for param in params:
            tags = find_tags(root, param)
            for tag in tags:
                tag.extract()

    def _clean_content_before(self, root, param):
        tag = find_tag(root, param)
        if tag is not None:
            siblings = []
            for sibling in tag.previous_siblings:
                siblings.append(sibling)
            for sibling in siblings:
                sibling.extract()
            tag.extract()

    def _clean_content_after(self, root, param):
        tag = find_tag(root, param)
        if tag is not None:
            siblings = []
            for sibling in tag.next_siblings:
                siblings.append(sibling)
            for sibling in siblings:
                sibling.extract()
            tag.extract()

    def _find_content_tag(self):
        return None

    def parse_content(self, root):
        assert self.parser_cls is not None
        p = self.parser_cls(root, self.url)
        return p()


class JsonExtractor(ExtractorInterface):
    def __init__(self, document, url=None):
        self.origin = document
        self.url = url
        self.before_init()
        try:
            self.data = json.loads(self.origin)
        except Exception:
            self.data = dict()
        self.after_init()

    def before_init(self):
        pass

    def after_init(self):
        pass

    def extract_title(self, param):
        pass

    def extract_date(self, param):
        pass

    def extract_source(self, param):
        pass

    def extract_author(self, param):
        pass

    def extract_editor(self, param):
        pass

    def extract_summary(self, param):
        pass

    def extract_tags(self, param):
        pass

    def extract_content(self, param, **kwargs):
        pass

    @staticmethod
    def wrap_body(body):
        body = u"<div id='hello_article'>{0}</div>".format(body)
        soup = BeautifulSoup(body, "lxml")
        return soup.find(name="div", id="hello_article")
