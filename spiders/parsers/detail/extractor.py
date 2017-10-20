# coding: utf-8

"""内容抽取相关的类"""

import re
from urlparse import urljoin
from bs4 import Tag
from parse import V1Parser, MosaicParser, store_tag
from score import score_news_content
from utils import clean_date_time
from html import extract_tag_attribute
from html import find_tag, find_tags
from html import unescape
from html5 import AllowTags
from cleaner import NewsCleaner, AdjustCleaner
from base import BaseExtractor, BaseCleaner, JsonExtractor

__author__ = "Sven Lee"
__copyright__ = "Copyright 2016-2019, ShangHai Lie Ying"
__credits__ = ["Sven Lee"]
__license__ = "Private"
__version__ = "1.0.0"
__email__ = "lee1300394324@gmail.com"
__date__ = "2016-05-09 13:58"


class SeparateExtractor(BaseExtractor):
    """老版本默认抽取器"""

    cleaner_cls = NewsCleaner
    parser_cls = V1Parser


class AdjustExtractor(BaseExtractor):
    """推荐使用的抽取器"""

    cleaner_cls = AdjustCleaner
    parser_cls = MosaicParser


class ScoreExtractor(AdjustExtractor):
    def _extract_title(self):
        param = {"params": {"name": "title"}}
        title = self._extract_tag(self.soup, param)
        return unescape(title)

    def _find_content_tag(self):
        return score_news_content(self._soup.body)


class News163Extractor(AdjustExtractor):
    class Cleaner163(BaseCleaner):
        """网易新闻轮播图在 textarea 标签中，不能移除 form 类标签"""
        allow_tags = AllowTags + ("textarea",)
        forms = False

    cleaner_cls = Cleaner163

    def extract_content(self, param, clean=None, before=None, after=None):
        roots = list()
        if param is None:
            roots.append(self._find_content_tag())
        elif isinstance(param, list):
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
            if root.name == "textarea":
                content.extend(self.parse_text_area(root))
            else:
                content.extend(self.parse_content(root))
        return self.clean_content(content)

    @staticmethod
    def parse_text_area(tag):
        content = list()
        if tag is None:
            return content
        tags = tag.find_all("li")
        for _tag in tags:
            for child in _tag.children:
                if not isinstance(child, Tag):
                    continue
                if child.name == "p" or child.name == "h2":
                    string = child.get_text().strip()
                    if string:
                        store_tag("p", {"text": string}, content)
                elif child.name == "i" and child.attrs.get("title") == "img":
                    src = child.get_text().strip()
                    if src:
                        store_tag("img", {"src": src}, content)
                else:
                    continue
        return content


class MoviesoonExtractor(SeparateExtractor):
    DIGITAL_MAPPING = {
        u"一": "01",
        u"二": "02",
        u"三": "03",
        u"四": "04",
        u"五": "05",
        u"六": "06",
        u"七": "07",
        u"八": "08",
        u"九": "09",
        u"十": "10",
        u"十一": "11",
        u"十二": "12",
    }

    def _extract_date(self):
        year_param = {
            "method": "find_all",
            "params": {"name": "span", "class_": "year"},
        }
        month_param = {
            "method": "find_all",
            "params": {"name": "span", "class_": "month"},
        }
        day_param = {
            "method": "find_all",
            "params": {"name": "span", "class_": "gun"},
        }
        year = self._extract_tag(self.soup, year_param)
        month = self._extract_tag(self.soup, month_param)
        day = self._extract_tag(self.soup, day_param)
        if len(year) != 4:
            return ""
        if len(day) == 1:
            day = "0" + day
        if month not in self.DIGITAL_MAPPING:
            return ""
        month = self.DIGITAL_MAPPING[month]
        time_tag = {
            "method": "find_all",
            "params": {"name": "div", "class_": "postAyrinti"},
        }
        time_string = self._extract_tag(self.soup, time_tag)
        return "-".join([year, month, day]) + time_string


class MyzakerExtractor(SeparateExtractor):
    def clean_source(self, source):
        param = {
            "method": "select",
            "params": {"selector": "div#news_template_03_AuthorAndTime > span"}
        }
        tag = find_tag(root=self.soup, param=param)
        text = extract_tag_attribute(root=tag)
        return source.replace(text, "")

    def clean_author(self, author):
        param = {
            "method": "select",
            "params": {"selector": "div#news_template_03_AuthorAndTime > span"}
        }
        tag = find_tag(root=self.soup, param=param)
        text = extract_tag_attribute(root=tag)
        return author.replace(text, "")


class ToutiaoGalleryExtractor(SeparateExtractor):
    class ToutiaoGalleryCleaner(BaseCleaner):
        scripts = False

    base_cleaner_cls = ToutiaoGalleryCleaner

    pattern = re.compile(r"'sub_abstracts': \[(.*)\],")

    def extract_content(self, param, clean=None, before=None, after=None):
        images = self.get_gallery()
        texts = self.get_text()
        return self.combine_gallery(images, texts)

    def get_gallery(self):
        param = {
            "method": "select",
            "params": {"selector": "div#tt-slide div.img-wrap"},
        }
        tags = find_tags(self.soup, param=param)
        images = list()
        for tag in tags:
            src = extract_tag_attribute(tag, name="data-src")
            images.append(src)
        return images

    def get_text(self):
        texts = list()
        matches = re.search(self.pattern, self.html)
        if not matches:
            return texts
        string = matches.group(1)
        if not string:
            return texts
        for text in string.split(","):
            text = text.decode("unicode-escape").strip()
            if text and text[1:-1].strip():
                texts.append(text)
        # string = string.decode("unicode-escape")
        # texts = [text.strip()[1:-1]
        #          for text in string.split(",")
        #          if text.strip()]
        return texts

    @staticmethod
    def combine_gallery(images, texts):
        content = list()
        length = len(texts)
        for i, image in enumerate(images):
            store_tag("img", {"src": image}, content)
            if i < length:
                store_tag("p", {"text": texts[i]}, content)
        return content


class G3163Extractor(JsonExtractor):
    def after_init(self):
        for key, value in self.data.items():
            if key in self.url:
                self.data = value
                break

    def extract_title(self, param):
        return self.data.get("title")

    def extract_date(self, param):
        date = self.data.get("ptime")
        if date:
            date = clean_date_time(date)
        return date

    def extract_source(self, param):
        return self.data.get("source")

    def extract_author(self, param):
        return None

    def extract_editor(self, param):
        return None

    def extract_summary(self, param):
        return None

    def extract_tags(self, param):
        return None

    def judge_missing(self, param):
        title = self.data.get("title")
        body = self.data.get("body")
        if not body:
            return False
        if u"安卓用户点这里" in body or u"最新版本客户端可获得更流畅体验" in body:
            return True
        if title and u"客户端版本需要升级" in title:
            return True
        if self.data.get("video"):
            return True
        return False

    def extract_content(self, param, **kwargs):
        body = self.data.get("body")
        images = self.data.get("img")
        if not (body or images):
            return list()
        for image in images:
            string = image["ref"]
            src = image["src"]
            tag = "<img src='{0}' />".format(src)
            body = body.replace(string, tag)
        tag = self.wrap_body(body)
        return MosaicParser(tag, self.url)()


class SinaPhotoExtractor(AdjustExtractor):
    def clean_title(self, title):
        words = title.split("_")
        if len(words) >= 3:
            return "_".join(words[:-2])
        return title

    def extract_content(self, param, clean=None, before=None, after=None):
        params = {"params": {"selector": "div#eData > dl"}, "method": "select"}
        img_params = {"params": {"selector": "dd:nth-of-type(1)"}, "method": "select"}
        text_params = {"params": {"selector": "dd:nth-of-type(5)"}, "method": "select"}
        dls = find_tags(self._soup, params)
        content = list()
        for dl in dls:
            image_tag = find_tag(dl, img_params)
            if not image_tag:
                continue
            url = extract_tag_attribute(image_tag, "text")
            if not (url and url.startswith("http") and url.endswith(".jpg")):
                continue
            content.append({"tag": "img", "src": url})
            text_tag = find_tag(dl, text_params)
            if not text_tag:
                continue
            text = extract_tag_attribute(text_tag, "text")
            if not text:
                continue
            text = text.replace("<br />", " ").strip()
            content.append({"tag": "p", "text": text})
        return self.clean_content(content)


class PcladyPhotoExtractor(AdjustExtractor):
    @staticmethod
    def find_tag_extract_attribute(root, params):
        tag = find_tag(root, params)
        if not tag:
            return None
        return extract_tag_attribute(tag, params.get("attribute", "text"))

    def extract_content(self, param, clean=None, before=None, after=None):
        content = list()
        first_text = {
            "params": {"selector": "p.picCont span.pic-txt"},
            "method": "select",
            "attribute": "text"
        }
        text = self.find_tag_extract_attribute(self._soup, first_text)
        if text:
            content.append({"tag": "p", "text": text})
        image_list = {
            "params": {"selector": "div.pic-scroll > ul > li > a > img"},
            "method": "select",
        }
        for a in find_tags(self._soup, image_list):
            src = extract_tag_attribute(a, "src")
            if src:
                content.append({"tag": "img", "src": src})
        for item in content:
            if item["tag"] == "img":
                item["src"] = item["src"].replace("_small", "").replace("_medium", "")
        return content


class IFengPhotoExtractor(AdjustExtractor):
    json_data_re = re.compile(r'var G_listdata=(.*?);', re.S)

    def get_json(self):
        from utils import parse_js
        json_text = self.json_data_re.findall(self.origin)
        if not json_text:
            return []
        json_text = json_text[0].strip()
        json_data = parse_js(json_text)
        return json_data

    def transe_to_unicode(self, text):
        from types import StringTypes, UnicodeType
        assert isinstance(text, StringTypes)
        if isinstance(text, UnicodeType):
            return text
        else:
            return text.decode("utf-8")

    def extract_content(self, param=None, clean=None, before=None, after=None):
        content = list()
        try:
            json_data = self.get_json()
        except Exception as e:
            json_data = list()
        for item in json_data:
            text = item.get("title", "")
            text = self.transe_to_unicode(text)
            src = item.get("big_img", "")
            content.append({"tag": "p", "text": text})
            content.append({"tag": "img", "src": src})
        return content


class HuanqiuPhotoExtractor(AdjustExtractor):
    class HuanqiuCleaner(BaseCleaner):
        scripts = False

    base_cleaner_cls = HuanqiuCleaner
    pattern_text = re.compile(r'"title":"(.*)",')
    pattern_image = re.compile(r'"img_url":"(.*)"}')

    def extract_content(self, param, clean=None, before=None, after=None):
        content = list()
        strings = re.findall(self.pattern_text, self.html)
        images = re.findall(self.pattern_image, self.html)
        if len(strings) != len(images):
            return content
        for i, image in enumerate(images):
            content.append({"tag": "img", "src": unescape(image)})
            if strings[i]:
                content.append({"tag": "p", "text": unescape(strings[i])})
        return content


class DuowanPhotoExtractor(AdjustExtractor):
    detail_url = "http://tu.duowan.com/index.php?r=show/getByGallery/&gid={id}"
    data = dict()

    def after_init(self):
        # 请用统一的方法重写此函数
        # (regex匹配、Json load、HTTP 请求 .etc.)
        print "init"
        import re
        import json
        import requests
        id_re = r'galleryId = "(.*?)";'
        id = re.findall(id_re, self.origin)
        if id:
            id = id[0]
            detail_url = self.detail_url.format(id=id)
            try:
                content = requests.get(detail_url).content
                self.data = json.loads(content)
            except:
                self.data = dict()
        else:
            self.data = dict()

    def transe_to_unicode(self, text):
        from types import StringTypes, UnicodeType
        assert isinstance(text, StringTypes)
        if isinstance(text, UnicodeType):
            return text
        else:
            return text.decode("utf-8")

    def extract_title(self, param):
        title = self.data.get("gallery_title", "")
        return title

    def extract_content(self, param, **kwargs):
        content_list = self.data.get("picInfo", [])
        content = list()
        for item in content_list:
            text = item.get("add_intro", "")
            text = self.transe_to_unicode(text)
            src = item.get("source", "")
            content.append({"tag": "p", "text": text})
            content.append({"tag": "img", "src": src})
        return content


class GuinnessExtractor(AdjustExtractor):
    @staticmethod
    def find_tag_extract_attribute(root, params):
        tag = find_tag(root, params)
        if not tag:
            return None
        return extract_tag_attribute(tag, params.get("attribute", "text"))

    def extract_content(self, param, clean=None, before=None, after=None):
        content = list()
        top_pic = {
            "params": {"selector": "div.region-inner > figure > img"},
            "method": "select",
            "attribute": "src"
        }
        pic_url = self.find_tag_extract_attribute(self._soup, top_pic)
        if pic_url:
            pic_url = urljoin(self.url, pic_url)
            content.append({"tag": "img", "src": pic_url})
        body_items = {
            "params": {"selector": "div.body-copy > div"},
            "method": "select",
        }
        img_src = {
            "params": {"selector": "img"},
            "method": "select",
            "attribute": "src"
        }
        for a in find_tags(self._soup, body_items):
            src = self.find_tag_extract_attribute(a, img_src)
            if src:
                src = urljoin(self.url, src)
                content.append({"tag": "img", "src": src})
            else:
                text = extract_tag_attribute(a, "text")
                if text.replace("&nbsp;", "").strip() != "":
                    content.append({"tag": "p", "text": text})
        return content


class NetEasePhotoExtractor(AdjustExtractor):
    json_data_re = re.compile(r'<textarea name="gallery-data" style="display:none;">(.*?)</textarea>', re.S)

    def get_json(self):
        from utils import parse_js
        json_text = self.json_data_re.findall(self.origin)
        if not json_text:
            return []
        json_text = json_text[0].strip()
        json_data = parse_js(json_text)
        return json_data.get("list", [])

    def transe_to_unicode(self, text):
        from types import StringTypes, UnicodeType
        assert isinstance(text, StringTypes)
        if isinstance(text, UnicodeType):
            return text
        else:
            return text.decode("utf-8")

    def extract_content(self, param=None, clean=None, before=None, after=None):
        content = list()
        try:
            json_data = self.get_json()
        except:
            json_data = list()
        for item in json_data:
            text = item.get("note", "")
            text = self.transe_to_unicode(text)
            src = item.get("oimg", "")
            content.append({"tag": "p", "text": text})
            content.append({"tag": "img", "src": src})
        return content


class SohuPhotoExtractor(AdjustExtractor):
    @staticmethod
    def find_tag_extract_attribute(root, params):
        tag = find_tag(root, params)
        if not tag:
            return None
        return extract_tag_attribute(tag, params.get("attribute", "text"))

    def extract_content(self, param, clean=None, before=None, after=None):
        content = list()
        first_text = {
            "params": {"selector": "p.explain"},
            "method": "select",
            "attribute": "text"
        }
        text = self.find_tag_extract_attribute(self._soup, first_text)
        if text:
            content.append({"tag": "p", "text": text})
        image_list = {
            "params": {"selector": "div.roll > div > ul > li  img"},
            "method": "select",
        }
        for a in find_tags(self._soup, image_list):
            src = extract_tag_attribute(a, "src")
            if src:
                content.append({"tag": "img", "src": src})
        for item in content:
            if item["tag"] == "img":
                item["src"] = item["src"].replace("stn", "n")
        return content


class XinshipuExtractor(AdjustExtractor):
    json_data_re = re.compile(r'<script type=\"application/ld\+json\">(.*?)</script>', re.S)
    none_re = re.compile(r'\s', re.S)  # 去除非法json空字符

    def after_init(self):
        from utils import parse_js
        json_text = self.json_data_re.findall(self.origin)
        if not json_text:
            self.json_data = []
        else:
            json_text = json_text[0].strip()
            json_text = self.none_re.subn("", json_text)[0]
            json_text = self.transe_to_unicode(json_text)
            json_data = parse_js(json_text)
            self.json_data = json_data

    def transe_to_unicode(self, text):
        from types import StringTypes, UnicodeType
        assert isinstance(text, StringTypes)
        if isinstance(text, UnicodeType):
            return text
        else:
            return text.decode("utf-8")

    def extract_title(self, param=None):
        title = self.json_data.get("name", u"")
        return self.transe_to_unicode(title)

    def extract_summary(self, param=None):
        summary = self.json_data.get("description", u"")
        return self.transe_to_unicode(summary)

    def _extract_author(self):
        author = self.json_data["author"]["name"]
        return self.transe_to_unicode(author)

    def extract_content(self, param=None, clean=None, before=None, after=None):
        content = list()
        top_pic = self.json_data.get("image", u"")
        top_pic = self.transe_to_unicode(top_pic)
        intro = self.json_data.get("description", u"")
        intro = self.transe_to_unicode(intro)
        met = self.json_data.get("recipeIngredient", [])
        met = u",".join(map(lambda x: self.transe_to_unicode(x), met))
        way = self.json_data.get("recipeInstructions", u"")
        way = self.transe_to_unicode(way)

        content.append({"tag": "img", "src": top_pic})
        content.append({"tag": "p", "text": u"简介:"})
        content.append({"tag": "p", "text": intro})
        content.append({"tag": "p", "text": u"材料:"})
        content.append({"tag": "p", "text": met})
        content.append({"tag": "p", "text": u"做法:"})
        for p in way.split(u"。"):
            content.append({"tag": "p", "text": p+u"。"})
        return content


MAPPING = {
    "default": AdjustExtractor,
    "moviesoon": MoviesoonExtractor,
    "myzaker": MyzakerExtractor,
    "toutiaogallery": ToutiaoGalleryExtractor,
    "news163": News163Extractor,
    "g3163": G3163Extractor,
    "sinaphoto": SinaPhotoExtractor,
    "pclady": PcladyPhotoExtractor,
    "ifengphoto": IFengPhotoExtractor,
    "huanqiuphoto": HuanqiuPhotoExtractor,
    "duowanphoto": DuowanPhotoExtractor,
    "guinness": GuinnessExtractor,
    "neteasepic": NetEasePhotoExtractor,
    "sohupic": SohuPhotoExtractor,
    "xinshipu": XinshipuExtractor,
}
