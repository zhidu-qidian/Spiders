# coding: utf-8

""" 特殊的解析, 列表页会根据 special_mapping 调用相应的解析函数

解析函数接受 document: str, url=None:str 两个参数,
返回 list of models.Fields.to_dict()
"""

import json

from .models import Fields
from .utils import clean_date_time
from .utils import get_string_md5


def baidu_list_parse(document, url=None):

    def wrap_content(title, content):
        html = """
        <!DOCTYPE html>
        <html lang="en">
        <head><meta charset="UTF-8"><title>{}</title></head>
        <body><div id="content">{}</div></body></html>
        """
        html_contents = []
        for i in content:
            if i["type"] == "image":
                pic = '<img src = "{}" width ={} height ={} />'
                pic_src = i["data"]["big"]["url"]
                pic_width = i["data"]["big"]["width"]
                pic_height = i["data"]["big"]["height"]
                html_contents.append(pic.format(pic_src, pic_width, pic_height))
            if i["type"] == "text":
                text = '<p>{}</p>'
                text_content = i["data"].encode("utf-8")
                html_contents.append(text.format(text_content))
        html = html.format(title.encode("utf-8"), "\n".join(html_contents))
        return html

    data = json.loads(document)
    feeds = data["data"].get("news") or data["data"].get("list") or list()
    result = list()
    for feed in feeds:
        fields = Fields()
        if not (feed.get("title") and feed.get("content")):
            continue
        title = feed["title"]
        fields.title = title
        fields.url = "http://www.lieying-fakebaidu.com/" + get_string_md5(title)
        fields.publish_site = feed.get("site", "")
        fields.publish_time = clean_date_time(feed.get("ts", ""))
        fields.abstract = feed.get("long_abs", "")
        fields.html = wrap_content(title, content=feed.get("content"))
        result.append(fields.to_dict())
    return result


# 特殊解析映射表
special_mapping = {
    "s_baidu": baidu_list_parse,
}
