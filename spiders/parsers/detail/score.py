# coding: utf-8

"""通过打分定位内容节点"""

from bs4 import BeautifulSoup, Tag, NavigableString

__author__ = "Sven Lee"
__copyright__ = "Copyright 2016-2019, ShangHai Lie Ying"
__credits__ = ["Sven Lee"]
__license__ = "Private"
__version__ = "1.0.0"
__email__ = "lee1300394324@gmail.com"
__date__ = "2016-05-12 17:34"


def score_news_content(root):
    mapping = _score(root)
    return _choose(root, mapping)


P_NAMES = ["p", "section"]


def _score(root):

    mapping = dict()

    def score(tag):
        if not isinstance(tag, (Tag, BeautifulSoup)):
            return
        mapping[tag] = 0.0
        p_length = len(tag.find_all(name=P_NAMES, recursive=False))
        weight = p_length if p_length > 0 else 1
        for child in tag.children:
            if isinstance(child, Tag):
                mapping[child] = mapping.get(child, 0.0)
                if child.name == "img":
                    if child.find_parent("a"):  # 带超链接的图片
                        pass
                    else:
                        mapping[child] += 3.0
                elif child.name in P_NAMES:
                    mapping[child] += 3.0
                    if child.img:
                        mapping[child] += 10.0
                    l = len(child.get_text().strip())
                    mapping[child] += l / 40 * 6 * weight
                else:
                    score(child)
                mapping[tag] += mapping[child]
            elif isinstance(child, NavigableString):
                if child.find_parent("a"):  # 带链接的文本
                    pass
                else:
                    mapping[tag] += len(unicode(child).strip()) / 40 * 3
            else:
                pass
    score(root)
    return mapping


def _choose(root, mapping):
    score = mapping[root]
    tag = root
    min_score = score
    content_tags = root.find_all(name=["div", "article"])
    for child in content_tags:
        c_score = mapping.get(child, 0.0)
        if 0.6 * score < c_score <= min_score:
            min_score = c_score
            tag = child
    return None if tag.name == "body" else tag
