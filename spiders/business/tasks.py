# coding: utf-8

""" 爬虫各个任务 """

from collections import OrderedDict
from datetime import datetime
import logging
import time

from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from spiders.business.cleaner import NewsCleaner
from spiders.business.cleaner import is_news_valid
from spiders.business.comments import get_comment_url
from spiders.business.consts import FORM_NEWS, FORM_VIDEO, FORM_ATLAS, FORM_JOKE, FORM_PICTURE
from spiders.business.subscribe import qdzx
from spiders.business.utils import COL_CONFIGS, COL_REQUESTS, COL_CHANNELS
from spiders.business.utils import COL_NEWS, COL_ATLAS, COL_JOKE, COL_VIDEO, COL_PICTURE
from spiders.business.utils import db_third_party as db
from spiders.business.utils import request_from_config_request
from spiders.business.utils import is_advertisement
from spiders.business import jokes as jparser
from spiders.business import videos as vparser
from spiders.business.videos import video_autohome_parser
from spiders.business.videos import video_meipai_parser
from spiders.business.videos import video_thepaper_parser
from spiders.business.videos import video_weibo_parser
from spiders.business.videos import video_yingtu_parser
from spiders.business.videos import video_miaopai_parser
from spiders.error import NotSupportError, ImageDownloadError
from spiders.images import choose_feed_images, download_and_upload_images
from spiders.images import get_feed_size
from spiders.models import NewsFields, ListFields, ForeignFields, AtlasFields
from spiders.parsers.detail import DetailParser
from spiders.parsers.feed import FeedParser
from spiders.parsers.page import PageParser
from spiders.utilities import get_string_md5, utc_datetime_now
from spiders.utilities import http, format_datetime_string, clean_date_time
from spiders.utilities import rebuild_url
from spiders.utilities.http import Request, response_url_content

PROCEDURE_LIST_TASK = 0  # 完成列表页解析状态
PROCEDURE_DOWNLOAD_TASK = 10000  # 完成详情页下载状态
PROCEDURE_DETAIL_TASK = 20000  # 完成详情页解析状态
PROCEDURE_DETAIL_NOT_SUPPORT_DOMAIN = 21000  # 详情页解析不支持当前域名
PROCEDURE_DETAIL_MISS_FIELD = 22000  # 解析不出已知的字段
PROCEDURE_CLEAN_TASK = 30000  # 完成清洗过滤状态
PROCEDURE_CLEAN_INVALID = 31000  # 不合法资讯状态
PROCEDURE_RESOURCE_TASK = 40000  # 完成资源处理状态
PROCEDURE_RESOURCE_DOWNLOAD_ERROR = 41000  # 资源下载失败状态
PROCEDURE_RESOURCE_UPLOAD_ERROR = 42000  # 资源上传失败状态
PROCEDURE_PREPARE_TASK = 50000  # 完成资讯字段准备状态
PROCEDURE_STORE_TASK = 60000  # 完成资讯分表存储状态
PROCEDURE_STORE_ERROR = 61000  # 存储失败
tmsnow = lambda: int(time.time()*1000)
tsnow = lambda: int(time.time())


def update_error_message(_id, message, procedure):
    query = {"_id": ObjectId(_id)}
    update = {"$set": {"error": message, "procedure": procedure}}
    db[COL_REQUESTS].update_one(query, update=update)


def _request_doc_from_config_channel(config, channel):
    doc = dict()
    doc["channel"] = config["channel"]
    doc["config"] = str(config["_id"])
    doc["form"] = channel["form"]
    doc["site"] = channel["site"]
    doc["time"] = utc_datetime_now()
    doc["fields"] = dict()
    doc["unique"] = ""
    doc["procedure"] = -1
    return doc


# 新闻,图集特有
def run_list_task(_id, debug=False):
    """  列表页下载解析任务(耗时任务) 
    
    :param _id: thirdparty spider_config　表 _id
    :type _id: str
    :return: 新插入的 COL_REQUESTS 表的 _id 列表 
    :rtype: list of str
    """
    config = db[COL_CONFIGS].find_one({"_id": ObjectId(_id)})
    channel = db[COL_CHANNELS].find_one({"_id": ObjectId(config["channel"])})
    if channel["site"] == "585b6f3f3deaeb61dd2e288b":  # 百度参数需添加 ts 字段
        config["request"]["params"]["ts"] = [int(time.time())]
    elif channel["site"] == "5862342c3deaeb61dd2e2890":  # 号外参数需要添加 lastTime 字段
        config["request"]["params"]["lastTime"] = datetime.now().strftime("%Y%m%d%H%M%S")
    elif channel["site"] == "5875f46e3deaeb61dd2e2898":  # umei.cc 需要添加时间戳，保证页面更新
        config["request"]["params"]["_"] = [int(time.time())]
    elif channel["site"] == "57a4092eda083a0e80a709c1" and config["channel"] \
            in ["594b9a07921e6d1615df7afb", "594b99b6921e6d1615df7af9",
                "594b9985921e6d1615df7af7", "594b9951921e6d1615df7af5",
                "594b98fd921e6d1615df7af3"]:  # 新浪热点新闻需要添加 top_time 字段
        config["request"]["params"]["top_time"] = datetime.now().strftime("%Y%m%d")
    elif channel["site"] == "579ee39fda083a625d1f4ad5" and config["crawler"] == "toutiaoapp":
        ms = tmsnow()
        s = ms/1000
        config["request"]["params"]["_rticket"] = ms
        config["request"]["params"]["last_refresh_sub_entrance_interval"] = s
        config["request"]["params"]["min_behot_time"] = s - 7200
    req = request_from_config_request(config["request"])
    response = http.download(req)
    url, content = http.response_url_content(response)
    if channel["site"] == "5862342c3deaeb61dd2e2890":  # 号外列表页有下载
        result = parse_list_haowai(document=content, url=url)
    else:
        result = FeedParser(document=content, crawler=config["crawler"], url=url)
    if len(result) == 0:  # Todo: 列表页解析失败
        logging.error("List parse error channel: %s config: %s" % (config["channel"], _id))
        return None
    if debug:
        logging.info("List length: %s config: %s" % (len(result), _id))
        return result
    ids = list()
    for item in result:
        middle = _request_doc_from_config_channel(config, channel)
        fields = ListFields()
        fields.url = item["url"]
        fields.title = item.get("title", "")
        fields.publish_time = format_datetime_string(item.get("publish_time", ""))
        fields.publish_ori_name = item.get("publish_site") or item.get("author", "")
        fields.abstract = item.get("abstract", "")
        fields.tags = item.get("keywords", "")
        fields.html = item.get("html", "")
        if item.get("thumb"):
            fields.thumbs.append(item["thumb"])
        comment_id = item.get("comment_id", "")
        if comment_id:  # 为网易和天天快报生成评论抓取链接
            fields.comment = get_comment_url(channel["site"], comment_id)
        middle["list_fields"] = fields.to_dict()
        middle["pages"] = [{"url": item["url"], "html": ""}]
        middle["unique"] = item["url"]  # 以 url 作为唯一性约束,避免重复抓取 TODO: 归一化url
        middle["procedure"] = PROCEDURE_LIST_TASK
        try:
            r = db[COL_REQUESTS].insert_one(middle)  # fixme: 插入失败
        except DuplicateKeyError:
            pass
        except Exception as e:
            logging.error(e.message, exc_info=True)
        else:
            ids.append(str(r.inserted_id))
    return ids


# 新闻,图集特有
def run_download_task(_id, debug=False):
    """ 详情页下载任务,包含翻页判断与下载多个页面(耗时任务)
    
    :param _id: COL_REQUESTS 表 _id
    :type _id: str
    :return: COL_REQUESTS 表 _id
    :rtype: str
    """

    def new_page_object(_url, _html):
        return dict(url=_url, html=_html)

    def _download(url):
        req = Request.from_random_browser(url=url)
        try:
            response = http.download(req)
            url, content = response_url_content(response)
        except Exception:
            url, content = http.stable_download_content(url)
        return url, content

    query = {"_id": ObjectId(_id)}
    request = db[COL_REQUESTS].find_one(query)
    pages = list(request["pages"])
    list_fields = request.get("list_fields", dict())
    if list_fields.get("html"):
        pages[0]["html"] = list_fields["html"]
    else:
        current = pages[0]
        pages = list()
        url, content = _download(current["url"])
        pages.append(new_page_object(url, content))
        urls = PageParser(document=content, url=url)
        for u in urls:
            url, content = _download(u)
            pages.append(new_page_object(url, content))
    if debug:
        return pages
    update = {"$set": {"procedure": PROCEDURE_DOWNLOAD_TASK, "pages": pages}}
    db[COL_REQUESTS].update_one(query, update=update)
    return _id


# 新闻,图集特有
def run_detail_task(_id):
    """ 解析详情页(非耗时任务) 
    
    :param _id: COL_REQUESTS 表 _id
    :type _id: str
    :return: COL_REQUESTS 表 _id
    :rtype: str
    """
    query = {"_id": ObjectId(_id)}
    collection = db[COL_REQUESTS]
    request = collection.find_one(query)
    pages = request["pages"]
    if request["form"] == FORM_NEWS:
        news = NewsFields()
    elif request["form"] == FORM_ATLAS:
        news = AtlasFields()
    else:
        raise NotSupportError("run detail task not support %s" % request["form"])
    url, html = pages[0]["url"], pages[0]["html"]
    result = DetailParser(url=url, document=html)
    if not result["support"]:
        logging.error("Detail parse error(domain not support): %s" % _id)
        update = {"$set": {"procedure": PROCEDURE_DETAIL_NOT_SUPPORT_DOMAIN}}
    elif result["missing"]:
        logging.warning("Detail parse warn(miss some fields): %s" % _id)
        update = {"$set": {"procedure": PROCEDURE_DETAIL_MISS_FIELD}}
    else:
        news.title = result["title"]
        news.publish_time = format_datetime_string(result["date"])
        news.publish_ori_name = result["source"] or result["author"]
        if result["summary"]:
            news.abstract = result["summary"]
        if result["tags"]:
            news.tags = result["tags"]
        news.content = result["content"]
        news.publish_ori_url = url
        for page in request["pages"][1:]:
            result = DetailParser(url=page["url"], document=page["html"])
            news.content.extend(result["content"])
        update = {"$set": {"procedure": PROCEDURE_DETAIL_TASK, "fields": news.to_dict()}}
    collection.update_one(query, update=update)
    return _id if update["$set"]["procedure"] == PROCEDURE_DETAIL_TASK else None


# 通用步骤
def run_clean_filter_task(_id):
    """ 初步清洗,过滤资讯(非耗时任务) """
    query = {"_id": ObjectId(_id)}
    collection = db[COL_REQUESTS]
    projection = {"pages": 0}
    request = collection.find_one(query, projection=projection)
    form = request["form"]
    fields = request["fields"]
    list_fields = request.get("list_fields", dict())
    procedure = PROCEDURE_CLEAN_TASK
    update = {"$set": {"procedure": PROCEDURE_CLEAN_TASK, "fields": fields,
                       "list_fields": list_fields}}
    if form == FORM_NEWS or form == FORM_ATLAS:
        fields["title"] = NewsCleaner.clean_title(title=fields["title"])
        fields["content"] = NewsCleaner.clean_content(content=fields["content"])
        if not is_news_valid(fields):  # 新闻不合法
            logging.warning("Not valid news: %s" % _id)
            procedure = PROCEDURE_CLEAN_INVALID
        if list_fields and list_fields.get("title"):
            list_fields["title"] = NewsCleaner.clean_title(
                title=list_fields["title"])
    elif form == FORM_VIDEO:  # Todo: 清洗视频
        pass
    elif form == FORM_JOKE:  # Todo: 清洗段子
        pass
    else:
        raise NotSupportError("Not support clean request id: %s" % _id)
    update["$set"]["procedure"] = procedure
    collection.update_one(query, update=update)
    return _id if procedure == PROCEDURE_CLEAN_TASK else None


def news_resource_images(content, refer, form):
    procedure = PROCEDURE_RESOURCE_TASK
    n_images, n_videos, n_audios = 0, 0, 0
    image_urls = OrderedDict()
    for i, item in enumerate(content):
        if item["tag"] == "img":
            image_urls[i] = item["src"]
            item["org"] = item["src"]
            item["src"] = ""
            n_images += 1
        elif item["tag"] in ["video", "object"]:
            n_videos += 1
        elif item["tag"] == "audio":
            n_audios += 1
    if len(image_urls) != 0:  # 如果包含图片
        try:
            images = download_and_upload_images(image_urls.values(), refer=refer)
        except ImageDownloadError as e:
            procedure = PROCEDURE_RESOURCE_DOWNLOAD_ERROR
            logging.error(e.message)
        except Exception as e:
            procedure = PROCEDURE_RESOURCE_UPLOAD_ERROR
            logging.error(e.message, exc_info=True)
        else:
            for i, item in enumerate(image_urls.items()):
                index, _url = item
                image = images[i]
                image["ad"] = is_advertisement(image["md5"], _url)
                content[index].update(image)
    update = {"$set": {
        "fields.content": content,
        "fields.n_images": n_images,
        "procedure": procedure,
    }}
    if form == FORM_NEWS:
        update["$set"]["fields.n_videos"] = n_videos
        update["$set"]["fields.n_audios"] = n_audios
    return update


# 通用步骤
def run_resource_task(_id):
    """ 下载需要的资源(耗时任务) """
    query = {"_id": ObjectId(_id)}
    projection = {"fields": 1, "unique": 1, "form": 1, "list_fields": 1}
    col = db[COL_REQUESTS]
    r = col.find_one(query, projection=projection)
    refer = r["unique"] if r["unique"].startswith("http") else None
    form = r["form"]
    if form == FORM_NEWS or form == FORM_ATLAS:  # 处理新闻和图集的资源
        feeds = r["list_fields"].get("thumbs")
        if feeds:  # 处理列表页抓到的缩略图
            try:
                images = download_and_upload_images(feeds, refer=refer)
            except Exception as e:
                logging.error(e.message, exc_info=True)
                images = list()
            update = {"$set": {"list_fields.thumbs": images}}
            col.update_one(query, update=update)
        update = news_resource_images(r["fields"]["content"], refer, form)
    else:
        update = {"$set": {"procedure": PROCEDURE_RESOURCE_TASK}}
    col.update_one(query, update=update)
    return _id if update["$set"]["procedure"] == PROCEDURE_RESOURCE_TASK else None


# 通用步骤
def run_prepare_task(_id):
    """ 准备数据，生成一些必要的字段(耗时任务)
     
     为新闻生成 fields.gen_feeds 字段(列表页图)
    """
    query = {"_id": ObjectId(_id)}
    projection = {"fields": 1, "form": 1, "list_fields": 1}
    col = db[COL_REQUESTS]
    r = col.find_one(query, projection=projection)
    form = r["form"]
    if form == FORM_NEWS or form == FORM_ATLAS:  # 处理新闻需要的字段
        ori_feeds = r["list_fields"].get("thumbs", list())
        if ori_feeds:
            urls = [item["src"] for item in ori_feeds]
            ori_feeds = choose_feed_images(urls=urls, flag=False) if urls else list()
        urls = list()
        for item in r["fields"]["content"]:
            if item["tag"] == "img":
                w, h = get_feed_size(item.get("width", 0), item.get("height", 0))
                if w == 0 or h == 0 or item.get("qr") or item.get("gray") or item.get("ad"):
                    continue
                urls.append(item["src"])
        feeds = choose_feed_images(urls=urls) if urls else list()
        update = {"$set": {
            "procedure": PROCEDURE_PREPARE_TASK,
            "fields.gen_feeds": feeds,
            "fields.ori_feeds": ori_feeds,
        }}
    else:  # Todo: 处理其他资讯需要的字段
        update = {"$set": {"procedure": PROCEDURE_PREPARE_TASK}}
    col.update_one(query, update=update)
    return _id


# 通用步骤
def run_store_task(_id):
    """ requests 表中的内容分表存储 """
    mapping = {
        FORM_NEWS: COL_NEWS,
        FORM_VIDEO: COL_VIDEO,
        FORM_JOKE: COL_JOKE,
        FORM_ATLAS: COL_ATLAS,
        FORM_PICTURE: COL_PICTURE,
    }
    query = {"_id": ObjectId(_id)}
    projection = {"pages": 0}
    request = db[COL_REQUESTS].find_one(query, projection=projection)
    channel = db[COL_CHANNELS].find_one({"_id": ObjectId(request["channel"])})
    form = request["form"]
    foreign = ForeignFields()
    foreign.site = str(channel["site"])
    foreign.channel = str(channel["_id"])
    foreign.config = request.get("config", "")
    foreign.request = _id
    foreign.category1 = channel["category1"]
    foreign.category2 = channel.get("category2", "")
    foreign.priority = channel["priority"]
    list_fields = request.get("list_fields", dict())
    fields = request["fields"]
    for k, v in list_fields.items():
        if k in fields and k != "title" and v:
            fields[k] = v
    doc = dict(fields)
    doc["n_dislike"] = abs(doc["n_dislike"])
    doc.update(foreign.to_dict())
    update = {"$set": {"procedure": PROCEDURE_STORE_TASK}}
    try:
        r = db[mapping[form]].insert_one(doc)
    except Exception as e:
        logging.error(e.message, exc_info=True)
        update["$set"]["procedure"] = PROCEDURE_STORE_ERROR
    else:
        id = str(r.inserted_id)
        update["$set"]["store_id"] = id
        logging.info("Store %s: %s" % (form, id))
        data = {"col": mapping[form], "_id": id}
        qdzx(data)
    db[COL_REQUESTS].update_one(query, update)


# 视频特有
def run_video_task(_id, debug=False):
    """  视频抓取解析, 新建 requests 记录
    
    :param _id: config 表 _id
    :type _id: str
    :param debug: 测试标志
    :type debug: bool
    :return: requests 表 _id
    :rtype: str
    """
    site_parser_mapping = {
        "58be81943deaeb61dd2e28a6": video_meipai_parser,
        "583bc5155d272cd5c47a7668": video_weibo_parser,
        "57a43ec2da083a1c19957a64": video_thepaper_parser,
        "591ebb17ccb1365d651a43b8": video_autohome_parser,
        "598bd600921e6d6f9aa02667": video_yingtu_parser,
        "598bd839921e6d6f9aa0266b": video_miaopai_parser,
        "598bf7f5921e6d6faaa025f1": vparser.video_budejie_parser,
        "598bf9c9921e6d6faaa025f9": vparser.video_4399pk_parser,
        "598bfa8a921e6d6faaa025fd": vparser.video_gifcool_parser,
        "598c02ed921e6d6f9aa026b0": vparser.video_pearvideo_parser,
        "57bc0afeda083a1c19957b29": vparser.video_duowan_parser,
        "57c64e49fe8eca2b7946609a": vparser.video_ifeng_parser,
    }
    config = db[COL_CONFIGS].find_one({"_id": ObjectId(_id)})
    channel = db[COL_CHANNELS].find_one({"_id": ObjectId(config["channel"])})
    site_id = channel["site"]
    parser = site_parser_mapping.get(site_id)
    if not parser:
        raise NotSupportError("Not support parse video channel: %s" % config["channel"])
    url = config["request"]["url"]
    params = config["request"].get("params", dict())
    if params:
        url = rebuild_url(url,params)
    ids = list()
    videos = parser(url)
    if debug:
        return [video.to_dict() for video in videos]
    for video in videos:
        doc = _request_doc_from_config_channel(config, channel)
        doc["fields"] = video.to_dict()
        doc["unique"] = video.publish_ori_url
        doc["procedure"] = PROCEDURE_DETAIL_TASK
        try:
            r = db[COL_REQUESTS].insert_one(doc)  # fixme: 插入失败
        except DuplicateKeyError:
            pass
        except Exception as e:
            logging.error(e.message, exc_info=True)
        else:
            ids.append(str(r.inserted_id))
    return ids


# 段子特有
def run_joke_task(_id, debug=False):
    """ 段子抓取解析 """

    site_parser_mapping = {
        "591ebfd8ccb1365d651a43c2": jparser.joke_waduanzi_parser,
        "591ebf14ccb1365d651a43bf": jparser.joke_pengfu_parser,
        "59781274921e6d3682fab08c": jparser.joke_neihan_parser,
        "598bf748921e6d6f9aa02678": jparser.joke_caoegg_parser,
        "598bf7f5921e6d6faaa025f1": jparser.joke_budejie_parser,
        "598bfc10921e6d6faaa02601": jparser.joke_duanzidao_parser,
        "598bfd90921e6d6f9aa02692": jparser.joke_3jy_parser,
        "598bfe3e921e6d6faaa02605": jparser.joke_360wa_parser,
        "598bfec8921e6d6f9aa0269c": jparser.joke_fun48_parser,
        "598bff24921e6d6faaa02609": jparser.joke_biedoul_parser,
        "598bffa4921e6d6f9aa0269d": jparser.joke_nbsw_parser,
        "598c00da921e6d6faaa02610": jparser.joke_helegehe_parser,
        "598c0241921e6d6f9aa026ac": jparser.joke_khdx_parser,
    }
    config = db[COL_CONFIGS].find_one({"_id": ObjectId(_id)})
    channel = db[COL_CHANNELS].find_one({"_id": ObjectId(config["channel"])})
    site_id = channel["site"]
    parser = site_parser_mapping.get(site_id)
    if not parser:
        raise NotSupportError("Not support parse joke channel: %s" % config["channel"])
    url = config["request"]["url"]
    params = config["request"].get("params", dict())
    if params:
        url = rebuild_url(url, params)
    ids = list()
    jokes = parser(url)
    if debug:
        return [joke.to_dict() for joke in jokes]
    for joke in jokes:
        doc = _request_doc_from_config_channel(config, channel)
        doc["fields"] = joke.to_dict()
        doc["unique"] = get_string_md5(joke.text)
        doc["procedure"] = PROCEDURE_DETAIL_TASK
        try:
            r = db[COL_REQUESTS].insert_one(doc)
        except DuplicateKeyError:
            pass
        except Exception as e:
            logging.error(e.message, exc_info=True)
        else:
            ids.append(str(r.inserted_id))
    return ids


# 号外新闻
def parse_list_haowai(document, url=None):
    """ 号外新闻需要单独解析, 列表页有下载操作 """
    FIELDS = {"url", "title", "publish_time", "publish_site", "author",
              "abstract",
              "keywords", "comment_id"}

    class Fields(object):

        def __init__(self):
            for name in FIELDS:
                self.__dict__[name] = ""
                self.html = ""

        def to_dict(self):
            return dict(self.__dict__)

    def wrap_content(title, content):
        html = """
        <!DOCTYPE html>
        <html lang="en">
        <head><meta charset="UTF-8"><title>{}</title></head>
        <body><div id="content">{}</div></body></html>
        """
        html = html.format(title.encode("utf-8"), content.encode("utf-8"))
        return html

    import json
    url_format = "http://api.myhaowai.com/api/article/get_article_by_aid?aid={}&readFrom=app"
    data = json.loads(document)
    if not data or data["result"].get("code") == "1":
        return list()
    feeds = data.get("contentList", list())
    result = list()
    for feed in feeds:
        aid = feed.get("aid")
        if not aid:
            continue
        detail_url = url_format.format(aid)
        try:
            doc = http.download_json(url=detail_url)
            doc = doc["article_info"]
            content = http.download_json(doc["content_url"])
            content = content.get("content")
            title = doc["title"]
            if not (content and title):
                continue
            fields = Fields()
            fields.title = title
            fields.url = doc["content_url"]
            fields.publish_site = doc.get("nickname", "")
            fields.publish_time = clean_date_time(doc.get("pubtime", ""))
            fields.html = wrap_content(title=title, content=content)
        except Exception:
            raise
        else:
            result.append(fields.to_dict())
    return result

