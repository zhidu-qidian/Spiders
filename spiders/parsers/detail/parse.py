# coding: utf-8

"""内容递归解析"""

import re
from urlparse import urljoin
from types import StringType, UnicodeType, ListType
from bs4 import Tag, NavigableString

from html5 import AtomTags
from html5 import DropTags
from html5 import EmbedTag
from html5 import IframeTag
from html5 import ImageTag
from html5 import NewLineTags
from html5 import ObjectTag
from html5 import OlTag
from html5 import VideoTag
from html5 import TableTags
from html import extract_tag_attribute
from html import unwrap_child_tags

__author__ = "Sven Lee"
__copyright__ = "Copyright 2016-2019, ShangHai Lie Ying"
__credits__ = ["Sven Lee"]
__license__ = "Private"
__version__ = "1.0.0"
__email__ = "lee1300394324@gmail.com"
__date__ = "2016-05-09 17:48"

inline_names = {
    "a", "strong", "sup", "tt", "u",
    "b", "blod", "big", "i", "em", "italic", "small", "strike", "sub",
}

newline_tag_names = {"img", "div", "article", "p", "br", "section", "iframe"}
newline_head_names = {"h1", "h2", "h3", "h4", "h5", "h6"}
html_common_attributes = {
    "accesskey", "contenteditable", "contextmenu", "dir", "draggable",
    "dropzone", "hidden", "is", "itemid", "itemprop", "itemref", "itemscope",
    "lang", "spellcheck", "styple", "tabindex", "title", "translate", "class",
    "id",
}
img_content_attributes = {
    "alt", "src", "srcset", "sizes", "crossorigin", "usemap", "ismap", "width",
    "height", "referrerpolicy",
}


def get_tag_src(base_url, tag):
    """
    获取 img 标签的 src 属性, 由于很多 src 属性是通过其他字段通过 js 生成的,
    所以处理起来稍微复杂
    注意：若抽取不到则返回空字符串
    :param base_url:基础 url
    :type base_url:str
    :param tag:要获取的标签
    :type tag:Tag
    :return:抽取到的链接
    :rtype:str
    """
    attributes = []
    for attr in tag.attrs:
        attr_lower = attr.lower()
        if attr_lower in html_common_attributes or attr_lower in img_content_attributes:
            continue
        attribute = tag.get(attr)
        if isinstance(attribute, (StringType, UnicodeType)) and attribute.strip():
            attributes.append(tag.get(attr).strip())
    attributes.append(tag.get("src", "").strip())
    for attribute in attributes:
        attribute_lower = attribute.lower()
        if attribute_lower.startswith("http"):
            return attribute
        elif attribute_lower.startswith("./") \
                or attribute_lower.startswith("/") \
                or attribute_lower.startswith("//") \
                or attribute_lower.startswith("../"):
            return urljoin(base_url, attribute)
        elif attribute_lower.endswith(".jpg") \
                or attribute_lower.endswith(".png") \
                or attribute_lower.endswith(".gif") \
                or attribute_lower.endswith(".jpeg"):
            return urljoin(base_url, attribute)
        else:
            pass
    return ""


def get_video_src(tag, url=None):
    suffixes = {"swf", "flv", "mp4", "f4v"}
    src = tag.get("src", "").strip()
    if src:
        for suffix in suffixes:
            if src.endswith(suffix):
                return urljoin(url, src) if url else src
        if src.startswith("http"):
            return src
    for attr in tag.attrs:
        value = tag.get(attr)
        for suffix in suffixes:
            if value.endswith(suffix):
                return urljoin(url, src) if url else src
        if value.startswith("http"):
            return value
    return ""


def get_tag_attributes(tag, names=None):
    if names is None:
        names = set()
    attributes = dict()
    for attr in tag.attrs:
        l = attr.lower()
        if l in names:
            continue
        else:
            attribute = tag.get(attr)
            if isinstance(attribute, ListType):  # some attribute return list
                attribute = " ".join(attribute)
            attributes[l] = attribute
    return attributes


def only_contain_inline_names(root):
    """
    判断标签中是否只包含 inline 标签
    :param root:要判断的标签
    :type root:Tag
    :return:是否
    :rtype:bool
    """
    index, i = -1, 0
    br = None
    brs = len(root.find_all(name="br"))
    for i, child in enumerate(root.descendants):
        if not isinstance(child, Tag):
            continue
        if child.name == "br":
            index = i
            br = child
        elif child.name not in inline_names:
            return False
    if index == 0 or index == i:
        br.extract()
        brs -= 1
    if brs > 0:
        return False
    return True


def remove_tag_names(string, names):
    """
    移除string中的标签和属性
    :param string:要移除标签的字符串
    :type string:str
    :param names:要移除的标签名列表
    :type names:list of str or str
    :return:移除后的字符串
    :rtype:str
    """
    if isinstance(names, (list, tuple)):
        p_string = "|".join(["<{tag}[^>]*>|</{tag}>".format(tag=tag) for tag in names])
    else:
        p_string = "<{tag}[^>]*>|</{tag}>".format(tag=names)
    p = re.compile(p_string)
    return re.sub(p, "", string)


def remove_tag_name(string, name, count=0):
    start = "<{tag}[^>]*>".format(tag=name)
    end = "</{tag}>".format(tag=name)
    string = re.sub(start, "", string, count=count)
    if count == 0:
        count = 100000000
    while True:
        index = string.rfind(end)
        if index == -1 or count == 0:
            break
        else:
            string = string[:index] + string[index + len(end):]
            count -= 1
    return string


def store_tag(name, attributes, content):
    """
    保存名为 name, 包含 attributes 的标签到 content, inplace 操作
    :param name:标签名
    :type name:str
    :param attributes:标签的属性
    :type attributes:dict
    :param content:标签容器
    :type content:list of dict
    """
    tag = dict(attributes)
    tag["tag"] = name
    content.append(tag)


class BaseParser(object):

    def __init__(self, root, url):
        self.root = root
        self.url = url
        self.content = list()

    def store_tag(self, name, attributes):
        tag = dict(attributes)
        tag["tag"] = name
        self.content.append(tag)

    def store_text(self, string):
        text = "".join(string).strip() if isinstance(string, list) else string
        if text:
            attributes = {"text": text}
            self.store_tag("p", attributes)

    def store_atom(self, tag):
        string = tag.decode_contents()
        if tag.name == IframeTag:
            attributes = self.get_iframe_tag(tag)
        elif tag.name == VideoTag:
            attributes = self.get_video_tag(tag)
        elif tag.name == ObjectTag:
            attributes = self.get_object_tag(tag)
        elif tag.name == OlTag:
            attributes = self.get_ol_tag(tag)
        elif tag.name == EmbedTag:
            attributes = self.get_embed_tag(tag)
        else:
            attributes = dict()
        if tag.name in [VideoTag, IframeTag, EmbedTag] and not attributes:
            return
        if string.strip():
            attributes["text"] = string.strip()
        if attributes:
            self.store_tag(tag.name, attributes)

    def store_image(self, tag):
        src = get_tag_src(self.url, tag)
        if src:
            self.store_tag(tag.name, {"src": src})

    def get_iframe_tag(self, tag):
        src = get_tag_src(self.url, tag)
        attributes = dict()
        if src:
            attributes["src"] = src
        return attributes

    def get_video_tag(self, tag):
        src = extract_tag_attribute(tag, "src")
        controls = extract_tag_attribute(tag, "controls")
        poster = extract_tag_attribute(tag, "poster")
        attributes = dict()
        if src:
            attributes["src"] = src
        if controls:
            attributes["controls"] = controls
        if poster:
            attributes["poster"] = poster
        return attributes

    @staticmethod
    def get_object_tag(tag):
        data = extract_tag_attribute(tag, "data")
        attributes = dict()
        if data:
            attributes["data"] = data
        return attributes

    def get_embed_tag(self, tag):
        src = get_video_src(tag, self.url)
        if not src:
            return dict()
        attributes = get_tag_attributes(tag, ["width", "height", "id", "name", "src"])
        attributes["src"] = src
        return attributes

    @staticmethod
    def get_ol_tag(tag):
        type_ = extract_tag_attribute(tag, "type")
        reverse = extract_tag_attribute(tag, "reversed")
        attributes = dict()
        if type_:
            attributes["type"] = type_
        if reverse:
            attributes["reversed"] = reverse
        return attributes

    def parse(self, tag):
        raise NotImplementedError

    def __call__(self, *args, **kwargs):
        self.parse(self.root)
        return self.content


class V1Parser(BaseParser):

    def parse(self, tag):
        for child in tag.children:
            if isinstance(child, NavigableString):
                string = unicode(child).strip()
                self.store_text(string)
            elif isinstance(child, Tag):
                if child.name == "img":
                    self.store_image(child)
                elif child.name == "iframe":
                    src = get_tag_src(self.url, child)
                    if src:
                        attributes = {"src": src}
                        self.store_tag("iframe", attributes)
                elif only_contain_inline_names(child):
                    if not child.get_text().strip():
                        continue
                    string = remove_tag_names(unicode(child), names=child.name)
                    self.store_text(string)
                elif child.name in ["div", "section", "textarea"] \
                        or child.img or child.br or child.iframe:
                    self.parse(child)
                elif child.get_text().strip():
                    self.store_atom(child)


class MosaicParser(BaseParser):

    def parse(self, tag):
        strings = list()
        for child in tag.children:
            if isinstance(child, NavigableString):
                strings.append(unicode(child).strip())
            elif isinstance(child, Tag):
                if child.name in DropTags:
                    continue
                if child.name in NewLineTags:
                    self.store_text(strings)    # 进入下一段前，存储上一段的内容
                    strings = list()
                    if child.name == ImageTag:
                        self.store_image(child)
                    elif child.name == "table" and child.img:
                        self.unwrap_table_tags(child)
                        self.parse(child)
                    elif child.name in ["blockquote", "pre"] and child.img:
                        self.parse(child)
                    elif child.name in ["ul", "ol"] and child.img:
                        self.unwrap_ul_tags(child)
                        self.parse(child)
                    elif child.name == "dl" and child.img:
                        self.unwrap_dl_tags(child)
                        self.parse(child)
                    elif child.name in AtomTags:
                        if child.img or child.video or child.iframe:
                            self.parse(child)
                        else:
                            self.store_atom(child)
                    else:
                        self.parse(child)
                elif self.has_newline_tags(child):
                    self.parse(child)
                else:
                    if child.get_text().strip():
                        strings.append(unicode(child).strip())
            else:
                self.store_text(strings)
                strings = list()
        self.store_text(strings)

    @staticmethod
    def has_newline_tags(tag):
        for name in NewLineTags:
            if tag.find(name):
                return True
        return False

    @staticmethod
    def unwrap_table_tags(tag):
        unwrap_child_tags(tag, TableTags)

    @staticmethod
    def unwrap_ul_tags(tag):
        unwrap_child_tags(tag, ["li"])

    @staticmethod
    def unwrap_dl_tags(tag):
        unwrap_child_tags(tag, ["dd", "dt"])
