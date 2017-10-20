# coding: utf-8

"""
html5 标签说明
https://developer.mozilla.org/zh-CN/docs/Web/Guide/HTML/HTML5/HTML5_element_list
"""

__author__ = "Sven Lee"
__copyright__ = "Copyright 2016-2019, ShangHai Lie Ying"
__credits__ = ["Sven Lee"]
__license__ = "Private"
__version__ = "1.0.0"
__email__ = "lee1300394324@gmail.com"
__date__ = "2016-06-30 17:35"


# 根元素
RootTags = {"html"}
# 文档元数据
MetaDataTags = {"head", "title", "base", "link", "meta", "style"}
# 脚本
ScriptTags = {"script", "noscript", "template"}
# 章节
ChapterTags = {
    "body", "section", "nav", "article", "aside",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "header", "footer", "address", "main"
}
# 组织内容
OrganizeTags = {
    "p", "hr", "pre", "blockquote", "ol", "ul", "li", "dl", "dt", "dd",
    "figure", "figcaption", "div"
}
# 文字形式
TextTags = {
    "a", "em", "strong", "small", "s", "cite", "q", "dfn", "abbr", "data",
    "time", "code", "var", "samp", "kbd", "sub", "sup", "i", "b", "u", "mark",
    "ruby", "rt", "rp", "bdi", "bdo", "span", "br", "wbr"
}
# 编辑
EditTags = {"del", "ins"}
# 嵌入内容
EmbedTags = {
    "img", "iframe", "embed", "object", "param", "video", "audio", "source",
    "track", "canvas", "map", "area", "svg", "math"
}
# 表格
TableTags = {
    "table", "caption", "colgroup", "col", "tbody", "thead", "tfoot", "tr",
    "td", "th"
}
# 表单
FormTags = {
    "form", "fieldset", "legend", "label", "input", "button", "select",
    "datalist", "optgroup", "option", "textarea", "keygen", "output",
    "progress", "meter"
}
# 交互元素
InteractTags = {"details", "summary", "menuitem", "menu"}
# 弃用
Deprecated = {
    "applet", "basefont", "big", "blink", "center", "command", "content", "dir",
    "font", "frame", "frameset", "isindex", "keygen", "listing", "marquee",
    "nextid", "noembed", "plaintext", "spacer", "strike", "tt", "xmp",
}


NewLineTags = {
    "article", "section", "header", "footer", "address",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "p", "pre", "blockquote", "ol", "ul", "dl", "figure", "div", 
    "br", "hr",
    "img", "iframe", "object", "embed", "video", "math",
    "table",
    "figcaption",
    "form",
}

AtomTags = {
    "h1", "h2", "h3", "h4", "h5", "h6",
    "pre", "blockquote", "ol", "ul", "dl",
    "iframe", "video", "code", "object", "embed",
    "math",
    "table",
    "figcaption",
}

InlineTags = {
    "a", "em", "strong", "small", "s", "cite", "q", "dfn", "abbr", "time",
    "code", "var", "samp", "kbd", "sub", "sup", "i", "b", "u", "mark", "ruby",
    "rt", "rp", "bdi", "bdo", "span",
    "tt", "big", "strike", "del", "ins",
}

ImageTag = "img"
VideoTag = "video"
IframeTag = "iframe"
ObjectTag = "object"
EmbedTag = "embed"
OlTag = "ol"


AllowTags = (
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
    "td", "th",

    "noscript",
)

DropTags = (
    "noscript",
)
