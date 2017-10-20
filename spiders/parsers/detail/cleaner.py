# coding: utf-8

"""html清洗规则"""

from base import BaseCleaner
from html5 import AllowTags

__author__ = "Sven Lee"
__copyright__ = "Copyright 2016-2019, ShangHai Lie Ying"
__credits__ = ["Sven Lee"]
__license__ = "Private"
__version__ = "1.0.0"
__email__ = "lee1300394324@gmail.com"
__date__ = "2016-07-15 15:54"


class NewsCleaner(BaseCleaner):
    """老版本的基本新闻支持标签"""

    allow_tags = (
        "html", "head", "title", "body", "header",
        "div", "article", "section", "figure", "figcaption",
        "p", "h1", "h2", "h3", "h4", "h5", "h6",
        "a", "img", "br", "font",
        "b", "blod", "big", "i", "em", "italic", "small", "strike", "sub",
        "strong", "sup", "tt", "u",
        "textarea",
    )
    meta = True
    embedded = True
    frames = True
    forms = True


class AdjustCleaner(BaseCleaner):
    """新版新闻支持的标签，推荐使用

    "html",
    "head", "title",
    "body", "article", "section",
    "h1", "h2", "h3", "h4", "h5", "h6", "header", "footer", "address",
    "p", "hr", "pre", "blockquote", "ol", "ul", "li", "dl", "dt", "dd",
    "figure", "figcaption", "div",
    "a", "em", "strong", "small", "s", "cite", "q", "dfn", "abbr", "data",
    "time", "code", "var", "samp", "kbd", "sub", "sup", "i", "b", "u", "mark",
    "ruby", "rt", "rp", "bdi", "bdo", "span", "br", "wbr",
    "del", "ins",
    "img", "iframe", "embed", "object", "param", "video", "audio", "source",
    "track", "canvas", "map", "area", "svg", "math",
    "table", "caption", "colgroup", "col", "tbody", "thead", "tfoot", "tr",
    "td", "th"
    """
    allow_tags = AllowTags
    meta = True
    embedded = False
    frames = True
    forms = True
