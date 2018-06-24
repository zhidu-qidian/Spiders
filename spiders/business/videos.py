# coding: utf-8

""" 短视频相关解析

 1. 美拍
 2. 快手
 3. zaker
 4. 微博
 5. 澎湃新闻
 6. 汽车之家
"""

import json
from time import sleep
import re
from urllib import unquote_plus
from urlparse import urljoin, urlparse, parse_qs
from bs4 import BeautifulSoup
from w3lib.encoding import html_to_unicode

from spiders.models import VideoFields
from spiders.parsers.utils import extract_tag_attribute
from spiders.parsers.utils import get_tag_attribute, get_tag_attribute_int
from spiders.utilities import http, format_datetime_string, remove_url_query_params



def g_tags(string):
    words = string.split("#")
    return ";".join([word for i, word in enumerate(words) if i % 2 == 1])


def video_meipai_parser(url):
    documents = http.download_json(url=url)
    data = [doc["media"] for doc in documents if doc["type"] == "media"]
    videos = list()
    for item in data:
        video = VideoFields()
        video.title = item["caption"]
        video.publish_time = format_datetime_string(item["created_at"])
        video.publish_ori_url = item["url"]
        video.publish_ori_name = item["user"]["screen_name"]
        video.publish_ori_icon = item["user"]["avatar"]
        video.src = item["video"]
        video.thumbnail = item["cover_pic"]
        video.duration = int(item.get("time", 0))
        video.n_like = int(item.get("likes_count", 0))
        video.n_comment = int(item.get("comments_count", 0))
        video.n_repost = int(item.get("reposts_count", 0))
        video.tags = g_tags(video.title)
        videos.append(video)
    return videos


def video_kuaishou_parser(url):
    documents = http.download_json(url=url)
    data = documents.get("feeds", [])
    videos = list()
    for item in data:
        urls = item.get("main_mv_urls")
        thumbs = item.get("cover_thumbnail_urls")
        avatars = item.get("headurls")
        if not (urls and thumbs and avatars):
            continue
        video = VideoFields()
        video.title = item["caption"]
        video.publish_time = format_datetime_string(item["timestamp"])
        video.publish_ori_name = item["user_name"]
        video.publish_ori_url = avatars[0]["url"]
        video.src = urls[0]["url"]
        video.thumbnail = thumbs[0]["url"]
        video.duration = int(item["ext_params"].get("video", 0) / 1000.0)
        videos.append(video)
    return videos


def video_zaker_parser(url):
    document = http.download_json(url=url)
    data = document["data"].get("articles", [])
    videos = list()
    for item in data:
        url = item["full_url"]
        req = http.Request(url=url)
        try:
            response = http.download(req)
            doc = response.json()
        except Exception:
            continue
        detail = doc.get("data")
        if not detail:
            continue
        src = detail["video_info"]["url"]
        if src.endswith("m3u8"):
            src = src.replace("m3u8", "mp4")
        label = detail["video_info"]["video_label"].split(":")[::-1]
        duration = 0
        for n, i in enumerate(label):
            duration += pow(60, n) * int(i)
        video = VideoFields()
        video.title = item["title"]
        video.publish_ori_name = item["auther_name"]
        video.publish_ori_url = item["weburl"]
        video.publish_ori_icon = detail["article_group"]["logo"]["url"]
        video.thumbnail = detail["video_info"]["pic_url"]
        video.duration = duration
        video.src = src
        videos.append(video)
    return videos


def video_weibo_downloader(url):
    import requests
    with requests.Session() as session:
        session.cookies = requests.utils.cookiejar_from_dict(
            {"SUB": "_2AkMvnF44dcPhrAJWm_EXzGzqaIhH-jycSTfOAn7uJhMyAxh77nc-qSWPCC49JGeSHgISGwk67XxQvGhEsQ.."},
            cookiejar=None,
            overwrite=True
        )
        response = session.get(url, timeout=(10, 30))
        _, content = html_to_unicode(
            content_type_header=response.headers.get("content-type"),
            html_body_str=response.content
        )
        return content


def video_weibo_parser(url):
    body = video_weibo_downloader(url)
    weibo_video_url_re = re.compile(r"video_src=(.*?)&playerType")
    title_config = {"params": {"selector": "div.txt_cut"}, "method": "select"}
    publish_name_config = {"params": {"selector": "div.item_a"}, "method": "select"}
    publish_icon_config = {"params": {"selector": "img.face_pho"}, "method": "select"}
    thumbnail_config = {"params": {"selector": "img.piccut"}, "method": "select"}
    repost_config = {"params": {"selector": "li:nth-of-type(1) > a em:nth-of-type(2)"}, "method": "select"}
    comment_config = {"params": {"selector": "li:nth-of-type(2) > a em:nth-of-type(2)"}, "method": "select"}
    like_config = {"params": {"selector": "li:nth-of-type(3) > a em:nth-of-type(2)"}, "method": "select"}
    read_config = {"params": {"selector": "div.bot_number > em:nth-of-type(2)"}, "method": "select"}
    soup = BeautifulSoup(body, "lxml")
    tags = soup.select(selector="div.weibo_tv_frame > ul.li_list_1 > a")
    videos = list()
    for tag in tags:
        video = VideoFields()
        url = urljoin(url, extract_tag_attribute(tag, name="href"))
        try:
            content = video_weibo_downloader(url)
            video_url = unquote_plus(weibo_video_url_re.findall(content)[0])
            soup = BeautifulSoup(content, "lxml")
            root = soup.select_one("div.WB_handle > ul")
            video.n_repost = get_tag_attribute_int(root, repost_config)
            video.n_comment = get_tag_attribute_int(root, comment_config)
            video.n_like = get_tag_attribute_int(root, like_config)
            video.n_read = get_tag_attribute_int(soup, read_config)
        except Exception:
            continue
        if "miaopai" not in video_url:
            continue
        video.src = remove_url_query_params(video_url)
        video.publish_ori_url = url
        video.title = get_tag_attribute(tag, title_config, "text")
        video.publish_ori_name = get_tag_attribute(tag, publish_name_config, "text")
        video.thumbnail = get_tag_attribute(tag, thumbnail_config, "src")
        video.publish_ori_icon = get_tag_attribute(tag, publish_icon_config, "src")
        video.duration = 0
        video.tags = g_tags(video.title)
        videos.append(video)
    return videos


def video_thepaper_parser(url):
    body = http.download_html(url=url)
    thepaper_video_url_re = re.compile(r'source src="(.*?)" type="video/mp4"')
    detail_config = {"params": {"selector": "a"}, "method": "select"}
    title_config = {"params": {"selector": "div.video_title"}, "method": "select"}
    user_name_config = {"params": {"selector": "div.t_source > a"}, "method": "select"}
    thumbnail_config = {"params": {"selector": "div.video_list_pic > img"}, "method": "select"}
    user_icon_config = {"params": {"selector": "div.video_txt_r_icon img"}, "method": "select"}
    duration_config = {"params": {"selector": "div.video_list_pic > span.p_time"}, "method": "select"}
    comment_config = {"params": {"selector": "div.t_source > span.reply"}, "method": "select"}
    description_config = {"params": {"selector": "p"}, "method": "select"}
    soup = BeautifulSoup(body, "lxml")
    tags = soup.select(selector=".video_news")
    videos = list()
    for tag in tags:
        url = urljoin("http://www.thepaper.cn/", get_tag_attribute(tag, detail_config, "href"))
        try:
            req = http.Request(url=url)
            response = http.download(req)
            _, content = http.response_url_content(response)
            video_url = unquote_plus(thepaper_video_url_re.findall(content)[0])
        except Exception:
            continue
        video = VideoFields()
        video.title = get_tag_attribute(tag, title_config, "text")
        video.src = video_url
        video.publish_ori_url = url
        video.publish_ori_name = get_tag_attribute(tag, user_name_config, "text")
        video.publish_ori_name = video.publish_ori_name.replace(u"@所有人", u"澎湃视频")
        video.thumbnail = get_tag_attribute(tag, thumbnail_config, "src")
        video.n_comment = get_tag_attribute_int(tag, comment_config, "text")
        video.description = get_tag_attribute(tag, description_config, "text")
        string = get_tag_attribute(tag, duration_config, "text")
        if string:
            try:
                m, s = string.split(":")
                second = int(m) * 60 + int(s)
            except Exception:
                pass
            else:
                video.duration = second
        detail = BeautifulSoup(content, "lxml")
        video.publish_ori_icon = get_tag_attribute(detail, user_icon_config, "src")
        videos.append(video)
    return videos


def video_autohome_parser(url):
    body = http.download_html(url=url)
    autohome_vid_re = re.compile(r'vid=(.*?)&|vid: \"(.*?)\"')
    video_info_url_template = "http://p-vp.autohome.com.cn/api/gmi?mid={mid}&useragent=Android"
    title_config = {"params": {"selector": "div.video-item-tit > a"}, "method": "select"}
    detail_config = {"params": {"selector": "div.video-item-tit > a"}, "method": "select"}
    publish_time_config = {"params": {"selector": "div:nth-of-type(3) span:nth-of-type(3)"}, "method": "select"}
    publish_name_config = {"params": {"selector": "a#author_nickName"}, "method": "select"}
    publish_icon_config = {"params": {"selector": "img#author_headimageurl"}, "method": "select"}
    comment_config = {"params": {"selector": "span.videocom"}, "method": "select"}
    read_config = {"params": {"selector": "span.count-eye"}, "method": "select"}
    soup = BeautifulSoup(body, "lxml")
    tags = soup.select(selector="div.video-item")
    videos = list()
    for tag in tags:
        video = VideoFields()
        video.title = get_tag_attribute(tag, title_config, "text")
        video.publish_time = get_tag_attribute(tag, publish_time_config, "text")
        video.publish_time = format_datetime_string(video.publish_time)
        video.n_comment = get_tag_attribute_int(tag, comment_config, "text")
        video.n_read = get_tag_attribute_int(tag, read_config, "text")
        detail_url = urljoin(url, get_tag_attribute(tag, detail_config, "href"))
        try:
            req = http.Request(url=detail_url)
            response = http.download(req)
            _, content = http.response_url_content(response)
            vid_one, vid_two = autohome_vid_re.findall(content)[0]
            vid = vid_one if vid_one else vid_two
            soup = BeautifulSoup(content, "lxml")
            ts = soup.select("div.card-label > a") or soup.select("a.video-label")
            video.tags = ";".join([extract_tag_attribute(t, "text") for t in ts])
            kinenames = ";".join([extract_tag_attribute(t, "text") for t in soup.select("a.kindname")])
            if kinenames:
                video.tags += ";" + kinenames
            video.publish_ori_name = get_tag_attribute(soup, publish_name_config, "text")
            video.publish_ori_icon = get_tag_attribute(soup, publish_icon_config, "src")
            if video.publish_ori_icon:
                _u = urljoin(url, video.publish_ori_icon)
                video.publish_ori_icon = remove_url_query_params(_u)
        except Exception:
            continue
        info_url = video_info_url_template.format(mid=vid)
        try:
            req = http.Request(url=info_url)
            response = http.download(req)
            content = response.body[5:-1]
            info = json.loads(content)
        except Exception as e:
            try:
                content = response.body
                info = json.loads(content)
            except:
                continue
        if int(info["status"]) == 0:
            continue
        video.src = remove_url_query_params(info["copies"][-1]["playurl"])
        video.publish_ori_url = detail_url
        video.thumbnail = info["img"]
        video.duration = int(info["duration"])
        videos.append(video)
        sleep(0.2)
    return videos


def video_ifeng_parser(url):
    # http://v.ifeng.com/vlist/channel/85/showData/first_more.js
    body = http.download_html(url=url)[10:-2]
    detail_url_config = {"params": {"selector": "a"}, "method": "select"}
    video_info_re = re.compile(r"var videoinfo =(.*?);", re.S)
    video_src_re = re.compile(r'"gqSrc":"(.*?)"')
    soup = BeautifulSoup(body, "lxml")
    tags = soup.select(selector="ul > li")
    videos = list()

    def get_detail_content(detail_url):
        detail_html = http.download_html(url=detail_url)
        video_info = video_info_re.findall(detail_html)[0]
        video_info = video_info.replace("'", '"')
        video_json = json.loads(video_info)
        return video_json

    def get_video_src(id):
        video_info_url = "http://tv.ifeng.com/h6/{}_/video.json".format(id)
        v_content = http.download_html(url=video_info_url)
        result = video_src_re.findall(v_content)
        print result
        if result:
            return result[0]
        else:
            return None

    for tag in tags:
        video = VideoFields()
        video.publish_ori_url = get_tag_attribute(tag, detail_url_config, "href")
        detail_info = get_detail_content(video.publish_ori_url)
        video.title = detail_info["name"]
        video.publish_time = detail_info["createdate"]
        video.publish_time = format_datetime_string(video.publish_time)
        video.tags = ";".join(detail_info["keywords"].split())
        video.publish_ori_name = "凤凰视频"
        video.publish_ori_icon = None
        video.thumbnail = detail_info["videoLargePoster"]
        video.duration = int(detail_info["duration"])
        id = detail_info["id"]
        video.src = get_video_src(id)
        videos.append(video)
        sleep(0.2)
    return videos


def video_miaopai_parser(url):
    # 根据秒拍号进行列表抓取
    body = http.download_html(url=url)
    video_url_template = "http://gslb.miaopai.com/stream/{id}.mp4"
    detail_url_template = "http://www.miaopai.com/show/{id}.htm"
    vid_re = re.compile('data-scid="(.*?)"')
    cover_re = re.compile('data-img="(.*?)"')
    title_config = {"params": {"selector": "div.viedoAbout > p"}, "method": "select"}
    publish_name_config = {"params": {"selector": "p.personalDataN"}, "method": "select"}
    publish_icon_config = {"params": {"selector": "a.pic > img"}, "method": "select"}
    read_config = {"params": {"selector": "p.personalDataT > span.red"}, "method": "select"}
    tag_config = {"params": {"selector": "div.viedoAbout > p.orange"}, "method": "select"}
    num_like_config = {"params": {"selector": "ul.commentLike > li > a"}, "method": "select"}
    num_comment_config = {"params": {"selector": "ul.commentLike a.commentIco"}, "method": "select"}
    soup = BeautifulSoup(body, "lxml")
    tags = soup.select(selector="div.contentLeft > div.videoCont")
    videos = list()
    for tag in tags:
        video = VideoFields()
        vid = vid_re.findall(str(tag))
        vid = vid[0]
        video.title = get_tag_attribute(tag, title_config, "text")
        video.n_comment = get_tag_attribute_int(tag, num_comment_config, "text")
        video.n_read = get_tag_attribute_int(tag, read_config, "text")
        video.n_like = get_tag_attribute_int(tag, num_like_config, "text")
        video.tags = get_tag_attribute(tag, tag_config, "text")
        video.tags = ";".join(filter(lambda y: y != "", map(lambda x: x.strip(), video.tags.split("#"))))
        video.publish_ori_name = get_tag_attribute(soup, publish_name_config, "text")
        video.publish_ori_icon = get_tag_attribute(soup, publish_icon_config, "src")
        video.src = video_url_template.format(id=vid)
        video.publish_ori_url = detail_url_template.format(id=vid)
        video.thumbnail = cover_re.findall(str(tag))[0]
        videos.append(video)
        sleep(0.2)
    return videos


def video_yingtu_parser(url):
    # https://app.yingtu.co/v1/interaction/topic/video/list  [post]
    # {"data":{"topicId":"861232236534439936","pageId":0},"userId":"1501646183777","source":"h5"}:
    def download_this(url):
        import requests
        from urlparse import urlparse
        from urlparse import parse_qs
        a = urlparse(url)
        query_field = parse_qs(a.query)
        tid = query_field["topicId"][0]
        uid = query_field["userId"][0]
        params = '{"data":{"topicId":"%s","pageId":0},"userId":"%s","source":"h5"}'
        params = params % (tid, uid)
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        url_base = "https://app.yingtu.co/v1/interaction/topic/video/list"
        resp = requests.post(url=url_base, data=params, headers=headers)
        return resp.json()

    def format_duration(d_text):
        duration = map(lambda x: int(x), d_text.split(":"))
        duration = filter(lambda y: y != 0, duration)
        length = len(duration)
        result = 0
        for i in range(length, 0, -1):
            result += duration[length - i] * pow(60, i - 1)
        return int(result)

    json_data = download_this(url)
    item_list = json_data["data"].get("videoList", [])
    videos = list()
    for item in item_list:
        video = VideoFields()
        video.title = item["videoName"]
        video.publish_ori_name = item["creatorName"]
        video.publish_ori_url = item["videoPlayUrl"]
        video.thumbnail = item["videoCoverUrl"]
        video.duration = item["videoDuration"]
        video.duration = format_duration(video.duration)
        video.src = item["videoPlayUrl"]
        video.publish_time = format_datetime_string(item['createTime'])
        video.n_read = int(item["videoPlayCount"])
        video.n_repost = int(item["videoShareCount"])
        video.n_like = int(item["videoFavorCount"])
        videos.append(video)
    return videos


def video_duowan_parser(url):
    detail_info_template = "http://video.duowan.com/jsapi/playPageVideoInfo/?vids={vid}"
    detail_url_config = {"params": {"selector": "a.uiVideo__ori"}, "method": "select"}
    video_src_re = re.compile('<video src="(.*?)" id="video"')
    body = http.download_html(url=url)
    soup = BeautifulSoup(body, "lxml")
    tags = soup.select(selector="div.uiVideo__item")
    videos = list()
    for tag in tags:
        video = VideoFields()
        detail_url = get_tag_attribute(tag, detail_url_config, "href")
        vid = detail_url.split("/")[-1].strip(".html")
        m_detail_url = detail_url.replace(".com/", ".cn/")
        detail_json_url = detail_info_template.format(vid=vid)
        jsond_data = http.download_json(url=detail_json_url)
        video_info = jsond_data[vid]
        video.title = video_info["video_title"]
        video.n_comment = int(video_info["video_raw_comment_num"])
        video.n_read = video_info["video_raw_play_num"]
        video.n_like = int(video_info["video_raw_support"])
        video.tags = ";".join(video_info["video_tags"])
        video.publish_ori_name = video_info["user_nickname"]
        video.publish_ori_icon = video_info["user_avatar"]
        video.publish_time = format_datetime_string(video_info["video_upload_time"])
        video.publish_ori_url = video_info["video_url"]
        video.thumbnail = video_info["video_big_cover"]
        video.duration = int(video_info["video_raw_duration"])
        m_detail_content = http.download_html(url=m_detail_url)
        video.src = video_src_re.findall(m_detail_content)[0]
        videos.append(video)
        sleep(0.2)
    return videos


def video_acfun_parser(url):
    # http://www.acfun.cn/list/getlist?channelId=134&sort=0&pageSize=20&pageNo=1

    def get_video_src(vid):
        # 获取视频地址
        main_parse_url = "http://www.acfun.tv/video/getVideo.aspx?id=%s" % vid
        info = http.download_json(url=main_parse_url)
        sourceType = info['sourceType']
        if sourceType != 'zhuzhan':
            return []
        encode = info['encode']
        pass
        return vid

    json_data = http.download_json(url=url)
    item_list = json_data["data"]["data"]
    videos = list()
    for item in item_list:
        video = VideoFields()
        video.title = item["title"]
        video.n_comment = int(item["commentCount"])
        video.n_read = int(item["viewCountFormat"])
        video.n_like = None
        video.tags = None
        video.publish_ori_name = item["username"]
        video.publish_ori_icon = item["userAvatar"]
        video.publish_time = format_datetime_string(item["contributeTimeFormat"])
        video.publish_ori_url = urljoin(url, item["link"])
        video.thumbnail = item["coverImage"]
        video.duration = int(item["duration"])
        vid = item["videoId"]
        video.src = get_video_src(vid)
        videos.append(video)
        sleep(0.2)
    return videos


def video_budejie_parser(url):
    detail_url_config = {"params": {"selector": "div.j-r-list-c-desc > a"}, "method": "select"}
    title_config = {"params": {"selector": "div.j-r-list-c-desc > a"}, "method": "select"}
    publish_name_config = {"params": {"selector": "div.u-txt > a"}, "method": "select"}
    publish_icon_config = {"params": {"selector": "div.u-img img"}, "method": "select"}
    publish_time_config = {"params": {"selector": "div.u-txt > span"}, "method": "select"}
    src_config = {"params": {"selector": "div.j-video-c > div.j-video"}, "method": "select"}
    cover_config = {"params": {"selector": "div.j-video-c > div.j-video"}, "method": "select"}
    duration_config = {"params": {"selector": "div.j-r-list-c > div.j-video-c"}, "method": "select"}
    num_like_config = {"params": {"selector": "li.j-r-list-tool-l-up > span"}, "method": "select"}
    num_dislike_config = {"params": {"selector": "li.j-r-list-tool-l-down > span"}, "method": "select"}
    num_comment_config = {"params": {"selector": "span.comment-counts"}, "method": "select"}
    num_repost_config = {"params": {"selector": "div.j-r-list-tool-ct-share-c > span"}, "method": "select"}
    body = http.download_html(url=url)
    soup = BeautifulSoup(body, "lxml")
    tags = soup.select(selector="div.j-r-list > ul > li")
    videos = list()
    for tag in tags:
        video = VideoFields()
        video.publish_ori_url = get_tag_attribute(tag, detail_url_config, "href")
        video.publish_ori_url = urljoin(url, video.publish_ori_url)
        video.title = get_tag_attribute(tag, title_config, "text")
        video.publish_ori_name = get_tag_attribute(soup, publish_name_config, "text")
        video.publish_ori_icon = get_tag_attribute(soup, publish_icon_config, "src")
        video.publish_time = get_tag_attribute(soup, publish_time_config, "text")
        video.src = get_tag_attribute(tag, src_config, "data-mp4")
        video.thumbnail = get_tag_attribute(tag, cover_config, "data-poster")
        video.n_like = get_tag_attribute_int(tag, num_like_config, "text")
        video.n_dislike = get_tag_attribute_int(tag, num_dislike_config, "text")
        video.n_comment = get_tag_attribute_int(tag, num_comment_config, "text")
        video.n_repost = get_tag_attribute_int(tag, num_repost_config, "text")
        video.duration = get_tag_attribute(tag, duration_config, "data-videoMlen")
        print video.duration
        videos.append(video)
        sleep(0.2)
    return videos


def video_gifcool_parser(url):
    # http://www.gifcool.com/xsp/
    def get_like_dislike(id):
        url = "http://www.gifcool.com/plus/digg_ajax_index.php?id=%s" % id
        content = http.download_html(url=url)
        n_like = int(num_like_config.findall(content)[0])
        n_dislike = int(num_dislike_config.findall(content)[0])
        return n_like, n_dislike

    detail_url_config = {"params": {"selector": "div.title  a"}, "method": "select"}
    title_config = {"params": {"selector": "div.title  a"}, "method": "select"}
    publish_time_config = {"params": {"selector": "span.g9.ml50"}, "method": "select"}
    src_config = {"params": {"selector": "video"}, "method": "select"}
    cover_config = {"params": {"selector": "video"}, "method": "select"}
    num_like_config = re.compile('<i class="up"></i>(\d+)<s>')
    num_dislike_config = re.compile('<i class="down"></i>(\d+)<s>')
    body = http.download_html(url=url)
    soup = BeautifulSoup(body, "lxml")
    tags = soup.select(selector="div.main > ul > li")
    videos = list()
    for tag in tags:
        video = VideoFields()
        video.publish_ori_url = get_tag_attribute(tag, detail_url_config, "href")
        video.publish_ori_url = urljoin(url, video.publish_ori_url)
        video.title = get_tag_attribute(tag, title_config, "text")
        video.publish_ori_name = "姐夫酷"
        video.publish_ori_icon = None
        video.publish_time = get_tag_attribute(soup, publish_time_config, "text")
        video.publish_time = format_datetime_string(video.publish_time)
        video.src = get_tag_attribute(tag, src_config, "src")
        video.thumbnail = get_tag_attribute(tag, cover_config, "poster")
        video.thumbnail = urljoin(url, video.thumbnail)
        vid = video.publish_ori_url.split("/")[-1].strip(".html")
        n_like, n_dislike = get_like_dislike(vid)
        video.n_like = n_like
        video.n_dislike = n_dislike
        videos.append(video)
        sleep(0.2)
    return videos


def video_4399pk_parser(url):
    # http://joke.4399pk.com/video/find.html#

    def get_num_comment(id):
        n_comment_url = "http://joke.4399pk.com/wap/funnycourse-num-id-%s" % id
        content = http.download_json(url=n_comment_url)
        n_comment = content["msg"]["vcomment"]
        return int(n_comment)

    def get_wap_detail(id):
        meta = {}
        detail_wap = "http://joke.4399pk.com/wap/video-content-id-%s.html" % vid
        content = http.download_json(detail_wap)
        soup = BeautifulSoup(content, "lxml")
        meta["name"] = get_tag_attribute(soup, publish_name_config, "text")
        meta["icon"] = get_tag_attribute(soup, publish_icon_config, "src")
        return meta

    def get_video_inf(id):
        pass

    detail_url_config = {"params": {"selector": "a.img"}, "method": "select"}
    title_config = {"params": {"selector": "div.tit"}, "method": "select"}
    num_like_config = {"params": {"selector": "div.info > span.fr > em"}, "method": "select"}
    publish_name_config = {"params": {"selector": "div.kind-user.cf > div.fl > p"}, "method": "select"}
    publish_icon_config = {"params": {"selector": "div.kind-user.cf img"}, "method": "select"}
    body = http.download_html(url=url)
    soup = BeautifulSoup(body, "lxml")
    tags = soup.select(selector="div.piclist > ul > li")
    videos = list()
    for tag in tags:
        video = VideoFields()
        video.publish_ori_url = get_tag_attribute(tag, detail_url_config, "href")
        video.title = get_tag_attribute(tag, title_config, "text")
        video.n_like = get_tag_attribute_int(tag, num_like_config, "text")
        vid = video.publish_ori_url.split("/")[-1].split(".")[0]
        video.n_comment = get_num_comment(vid)
        video.publish_ori_name = get_tag_attribute(soup, publish_name_config, "text")
        video.publish_ori_icon = get_tag_attribute(soup, publish_icon_config, "src")
        print video.duration
        videos.append(video)
        sleep(0.2)
    return videos


def video_pearvideo_parser(url):
    def format_duration(d_text):
        duration = map(lambda x: int(x), d_text.split(":"))
        duration = filter(lambda y: y != 0, duration)
        length = len(duration)
        result = 0
        for i in range(length, 0, -1):
            result += duration[length - i] * pow(60, i - 1)
        return int(result)

    def get_detail_info(url):
        meta = {}
        content = http.download_html(url=url)
        soup = BeautifulSoup(content, "lxml")
        meta["src"] = src_re.findall(content)[0]
        meta["name"] = get_tag_attribute(soup, publish_name_config, "alt")
        meta["icon"] = get_tag_attribute(soup, publish_icon_config, "src")
        meta["time"] = get_tag_attribute(soup, publish_time_config, "text")
        meta["thumbnail"] = get_tag_attribute(soup, cover_config, "src")
        return meta

    detail_url_config = {"params": {"selector": "a.vervideo-lilink"}, "method": "select"}
    title_config = {"params": {"selector": "div.vervideo-title"}, "method": "select"}
    duration_config = {"params": {"selector": "div.duration"}, "method": "select"}
    num_like_config = {"params": {"selector": "span.fav"}, "method": "select"}
    publish_name_config = {"params": {"selector": "div.thiscat img"}, "method": "select"}
    publish_icon_config = {"params": {"selector": "div.thiscat img"}, "method": "select"}
    cover_config = {"params": {"selector": "div#poster img"}, "method": "select"}
    publish_time_config = {"params": {"selector": "div.details-content div.date"}, "method": "select"}
    src_re = re.compile('dUrl="(.*?)"')
    body = http.download_html(url=url)
    soup = BeautifulSoup(body, "lxml")
    tags = soup.select(selector="li.categoryem ")
    videos = list()
    for tag in tags:
        video = VideoFields()
        video.publish_ori_url = get_tag_attribute(tag, detail_url_config, "href")
        video.publish_ori_url = urljoin(url, video.publish_ori_url)
        video.title = get_tag_attribute(tag, title_config, "text")
        video.duration = get_tag_attribute(tag, duration_config, "text")
        video.duration = format_duration(video.duration)
        video.n_like = get_tag_attribute_int(tag, num_like_config, "text")
        meta = get_detail_info(video.publish_ori_url)
        video.publish_ori_name = meta["name"]
        video.publish_ori_icon = meta["icon"]
        video.publish_time = meta["time"]
        video.publish_time = format_datetime_string(video.publish_time)
        video.thumbnail = meta["thumbnail"]
        video.src = meta["src"]
        videos.append(video)
        sleep(0.2)
    return videos


def video_shangyijiankang_parser(url):
    # http://api.sytown.cn/FrameWeb/FrameService/Api.ashx
    def download_this(url):
        import requests
        params = '{"_dataid":"VideoIndexNewestList","_datatype":"json","_pageindex": 1, "_pagesize": 10, "_param": {}, "_type": "getlistpage"}'
        resp = requests.post(url=url, data=params)
        return resp.json()

    def format_duration(d_text):
        duration = map(lambda x: int(x), d_text.split(":"))
        duration = filter(lambda y: y != 0, duration)
        length = len(duration)
        result = 0
        for i in range(length, 0, -1):
            result += duration[length - i] * pow(60, i - 1)
        return int(result)

    document = download_this(url)
    data = document["data"].get("List", [])
    videos = list()
    for item in data:
        video = VideoFields()
        video.title = item["Name"]
        video.publish_ori_name = "尚医健康"
        video.thumbnail = item["PicturePath"]
        duration = item["Duration"]
        video.duration = format_duration(duration)
        video.src = item["SourcePath"]
        video.tags = item["Label"]
        video.description = item["Description"]
        video.n_read = int(item["BrowseQuantity"])
        videos.append(video)
    return videos


if __name__ == "__main__":
    videos = video_autohome_parser("http://chejiahao.autohome.com.cn/Subject/VRecommend/Index")
    for video in videos:
        print video.src,video.title
        # video_budejie_parser("http://www.budejie.com/video/")
        # video_acfun_parser("http://www.acfun.cn/list/getlist?channelId=134&sort=0&pageSize=20&pageNo=1")
        # for test yingtu.co
        # from urllib import urlencode
        #
        # url = "https://app.yingtu.co/v1/interaction/topic/video/list"
        # data = {"topicId": "861232236534439936", "userId": "1501646183777"}
        # url = url + "?" + urlencode(data)
        # video_yingtu_parser(url)
