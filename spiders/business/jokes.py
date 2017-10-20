# coding: utf-8

""" 段子解析
 
 1. 内涵段子
 2. 网易段子
 3. 糗事百科
 4. 嘻嘻哈哈
 5. 捧腹网
 6. 挖段子
"""
from urlparse import urljoin
from bs4 import BeautifulSoup
from spiders.models import JokeFields
from spiders.parsers.utils import get_tag_attribute, get_tag_attribute_int
from spiders.utilities import http, format_datetime_string

__author__ = "lixianyang"
__email__ = "705834854@qq.com"
__date__ = "2017-05-18 11:19"


def joke_neihan_parser(url):
    document = http.download_json(url=url)
    groups = document["data"]["data"]
    jokes = list()
    for g in groups:
        g = g["group"]
        joke = JokeFields()
        joke.publish_ori_name = g["user"]["name"]
        joke.publish_ori_icon = g["user"]["avatar_url"]
        joke.publish_time = format_datetime_string(g["create_time"])
        joke.text = g["text"]
        joke.n_comment = int(g["comment_count"])
        joke.n_like = int(g["digg_count"])
        joke.n_dislike = int(g["bury_count"])
        # _comment_need = g["code"]  # 评论需要该字段
        jokes.append(joke)
    return jokes


def joke_netease_parser(url):
    document = http.download_json(url=url)
    data = document[u"段子"]
    jokes = list()
    for g in data:
        if g.get("imgsum", 0) == 0:
            joke = JokeFields()
            joke.title = g["title"]
            joke.publish_ori_name = g["source"]
            joke.text = g["digest"]
            joke.n_comment = int(g["replyCount"])
            joke.n_like = int(g["upTimes"])
            joke.n_dislike = int(g["downTimes"])
            # _comment_need = g["docid"]  # 评论需要该字段
            jokes.append(joke)
    return jokes


def joke_qiushi_parser(url):
    headers = {
        "User-Agent": "qiushibalke_10.8.1_WIFI_auto_19",
        "Source": "android_10.8.1",
        "Model": "Xiaomi/hydrogen/hydrogen:6.0.1/MMB29M/V7.5.6.0.MBCCNDE:user/release-keys",
        "Uuid": "IMEI_8728c26518fa3ae795a7f787073d375f",
        "Deviceidinfo": '{"DEVICEID": "862535037295724","SIMNO": "89860112817005617959","IMSI": "460012225499106","ANDROID_ID": "27dafccd6e32bfb2","SDK_INT": 23,"SERIAL"a882d7f9","MAC": "02:00:00:00:00:00","RANDOM": ""}'
    }
    req = http.Request(url=url, headers=headers)
    document = http.download_json(request=req)
    data = document["items"]
    jokes = list()
    for g in data:
        if not g.get("user"):
            continue
        joke = JokeFields()
        joke.publish_ori_name = g["user"]["login"]
        avatar = g["user"].get("thumb")
        if not avatar:
            continue
        if avatar.startswith("//"):
            avatar = "http:" + avatar
        joke.publish_ori_icon = avatar
        joke.publish_time = format_datetime_string(g["created_at"])
        joke.text = g["content"]
        joke.n_comment = int(g.get("comments_count", 0))
        if g.get("votes"):
            joke.n_like = int(g["votes"]["up"])
            joke.n_dislike = int(g["votes"]["down"])
        jokes.append(joke)
    return jokes


def joke_xiha_parser(url):
    def get_metas(ids):
        url = "http://dg.xxhh.com/getcnums/?__jsonp__=fn&ids={ids}".format(ids=",".join(ids))
        document = http.download_json(url=url, skip=(3, -1))
        metas = dict()
        for i, meta in enumerate(document.get("d", [])):
            metas[ids[i]] = (int(meta[0]), int(meta[1]), int(meta[2]))  # comment, like, dislike
        return metas

    user_config = {"params": {"selector": "div.user-info-username > a"}, "method": "select"}
    user_icon_config = {"params": {"selector": "div.user-avatar40 > a > img"}, "method": "select"}
    text_config = {"params": {"selector": "div.article > pre"}, "method": "select"}
    id_config = {"params": {"selector": "div.comment"}, "method": "select"}
    document = http.download_html(url=url)
    soup = BeautifulSoup(document, "lxml")
    tags = soup.select(selector="div.min > div.section")
    jokes = list()
    for tag in tags:
        joke = JokeFields()
        joke.publish_ori_name = get_tag_attribute(tag, user_config, "text")
        joke.publish_ori_icon = get_tag_attribute(tag, user_icon_config, "src")
        joke.text = get_tag_attribute(tag, text_config, "text")
        _id = get_tag_attribute(tag, id_config, "id")
        _id = _id.replace("comment-", "")
        joke.id = _id  # Note add id attribute, comment need this filed
        jokes.append(joke)
    metas = get_metas([joke.id for joke in jokes])
    for joke in jokes:
        meta = metas[joke.id]
        joke.n_comment, joke.n_like, joke.n_dislike = meta
        del joke.id
    return jokes


def joke_pengfu_parser(url):
    id_config = {"method": "select", "attribute": "id"}
    title_config = {"params": {"selector": "h1.dp-b > a"}, "method": "select"}
    text_config = {"params": {"selector": "div.content-img"}, "method": "select"}
    user_config = {"params": {"selector": "p.user_name_list > a"}, "method": "select"}
    user_icon_config = {"params": {"selector": "a.mem-header > img"}, "method": "select"}
    like_config = {"params": {"selector": "span.ding em"}, "method": "select"}
    dislike_config = {"params": {"selector": "span.cai em"}, "method": "select"}
    comment_config = {"params": {"selector": "span.commentClick em"}, "method": "select"}
    document = http.download_html(url=url)
    soup = BeautifulSoup(document, "lxml")
    tags = soup.select(selector="div.list-item")
    jokes = list()
    for tag in tags:
        joke = JokeFields()
        joke.title = get_tag_attribute(tag, title_config, "text")
        joke.publish_ori_name = get_tag_attribute(tag, user_config, "text")
        joke.publish_ori_icon = get_tag_attribute(tag, user_icon_config, "src")
        joke.text = get_tag_attribute(tag, text_config, "text")
        joke.n_comment = get_tag_attribute_int(tag, comment_config, "text")
        joke.n_like = get_tag_attribute_int(tag, like_config, "text")
        joke.n_dislike = get_tag_attribute_int(tag, dislike_config, "text")
        # code = get_tag_attribute(tag, id_config, "text")  # Comment need
        jokes.append(joke)
    return jokes


def joke_waduanzi_parser(url):
    title_config = {"params": {"selector": "h2.item-title > a"}, "method": "select"}
    text_config = {"params": {"selector": "div.item-content"}, "method": "select"}
    user_config = {"params": {"selector": "div.post-author > a"}, "method": "select"}
    # user_icon_config = {"params": {"selector": "div.post-author > img"}, "method": "select"}
    like_config = {"params": {"selector": "div.item-toolbar > ul > li:nth-of-type(1) > a"}, "method": "select"}
    dislike_config = {"params": {"selector": "div.item-toolbar > ul > li:nth-of-type(2) > a"}, "method": "select"}
    document = http.download_html(url=url)
    soup = BeautifulSoup(document, "lxml")
    tags = soup.select(selector="div.post-item")
    jokes = list()
    for tag in tags:
        joke = JokeFields()
        joke.title = get_tag_attribute(tag, title_config, "text")
        joke.publish_ori_name = get_tag_attribute(tag, user_config, "text")
        # joke.publish_ori_icon =get_tag_attribute(tag, user_icon_config, "src")
        joke.text = get_tag_attribute(tag, text_config, "text")
        joke.n_like = get_tag_attribute_int(tag, like_config, "text")
        joke.n_dislike = get_tag_attribute_int(tag, dislike_config, "text")
        jokes.append(joke)
    return jokes


def joke_nbsw_parser(url):
    text_config = {"params": {"selector": "div.ecae > p"}, "method": "select"}
    user_config = {"params": {"selector": "a.local-link"}, "method": "select"}
    user_icon_config = {"params": {"selector": "img.avatar"}, "method": "select"}
    like_config = {"params": {"selector": "div.count-box"}, "method": "select"}
    comment_config = {"params": {"selector": "span.wppviews"}, "method": "select"}
    pb_time_config = {"params": {"selector": "span.meta > abbr"}, "method": "select"}
    document = http.download_html(url=url)
    soup = BeautifulSoup(document, "lxml")
    tags = soup.select(selector="ul#postlist > li")
    jokes = list()
    for tag in tags:
        joke = JokeFields()
        joke.publish_ori_name = get_tag_attribute(tag, user_config, "text")
        joke.publish_ori_icon = get_tag_attribute(tag, user_icon_config, "src")
        joke.text = get_tag_attribute(tag, text_config, "text")
        joke.text = joke.text.strip("[...]")
        joke.n_like = get_tag_attribute_int(tag, like_config, "text")
        joke.n_comment = get_tag_attribute_int(tag, comment_config, "text")
        pb_time = get_tag_attribute(tag, pb_time_config, "text")
        joke.publish_time = format_datetime_string(pb_time)
        jokes.append(joke)
    return jokes


def joke_biedoul_parser(url):
    title_config = {"params": {"selector": "div.dz-list-con > a > p"}, "method": "select"}
    text_config = {"params": {"selector": "div.dz-list-con > p"}, "method": "select"}
    user_config = {"params": {"selector": "div.dz-username > a"}, "method": "select"}
    user_icon_config = {"params": {"selector": "div.user-portrait > img.avatar"}, "method": "select"}
    like_config = {"params": {"selector": "a.zanUp"}, "method": "select"}
    dislike_config = {"params": {"selector": "a.zanDown"}, "method": "select"}
    pb_time_config = {"params": {"selector": "div.dz-username > span"}, "method": "select"}
    document = http.download_html(url=url)
    soup = BeautifulSoup(document, "lxml")
    tags = soup.select(selector="div.lcommon.dz-bg > div")
    jokes = list()
    for tag in tags:
        joke = JokeFields()
        joke.title = get_tag_attribute(tag, title_config, "text")
        joke.publish_ori_name = get_tag_attribute(tag, user_config, "text")
        joke.publish_ori_icon = get_tag_attribute(tag, user_icon_config, "src")
        joke.text = get_tag_attribute(tag, text_config, "text")
        joke.n_like = get_tag_attribute_int(tag, like_config, "text")
        joke.n_dislike = get_tag_attribute_int(tag, dislike_config, "text")
        pb_time = get_tag_attribute(tag, pb_time_config, "text")
        joke.publish_time = format_datetime_string(pb_time)
        jokes.append(joke)
    return jokes


def joke_fun48_parser(url):
    def get_full_content(ori_url):
        text_config = {"params": {"selector": "article.article"}, "method": "select"}
        document = http.download_html(url=ori_url)
        soup = BeautifulSoup(document, "lxml")
        text = get_tag_attribute(soup, text_config, "text")
        return text

    title_config = {"params": {"selector": "div.texttitle > a"}, "method": "select"}
    ori_url_config = {"params": {"selector": "div.texttitle > a"}, "method": "select"}
    pb_time_config = {"params": {"selector": "div.card-info"}, "method": "select"}
    document = http.download_html(url=url)
    soup = BeautifulSoup(document, "lxml")
    tags = soup.select(selector="div#isonormal > div")
    jokes = list()
    for tag in tags:
        joke = JokeFields()
        joke.publish_ori_url = get_tag_attribute(tag, ori_url_config, "href")
        joke.text = get_full_content(joke.publish_ori_url)
        joke.title = get_tag_attribute(tag, title_config, "text")
        joke.text = joke.text.strip("[...]")
        pb_time = get_tag_attribute(tag, pb_time_config, "text")
        joke.publish_time = format_datetime_string(pb_time)
        jokes.append(joke)
    return jokes


def joke_360wa_parser(url):
    title_config = {"params": {"selector": "div.p_left > p.title1 > a"}, "method": "select"}
    text_config = {"params": {"selector": "div.p_left > p:nth-of-type(2)"}, "method": "select"}
    like_config = {"params": {"selector": "p.p_ding span"}, "method": "select"}
    document = http.download_html(url=url)
    soup = BeautifulSoup(document, "lxml")
    tags = soup.select(selector="div#recent > div.p1")
    jokes = list()
    for tag in tags:
        joke = JokeFields()
        joke.title = get_tag_attribute(tag, title_config, "text")
        joke.text = get_tag_attribute(tag, text_config, "text")
        joke.n_like = get_tag_attribute_int(tag, like_config, "text")
        jokes.append(joke)
    return jokes


def joke_3jy_parser(url):
    title_config = {"params": {"selector": "h2 > a"}, "method": "select"}
    text_config = {"params": {"selector": "div.c"}, "method": "select"}
    user_config = {"params": {"selector": "a.u_name"}, "method": "select"}
    like_config = {"params": {"selector": "p.zan"}, "method": "select"}
    dislike_config = {"params": {"selector": "p.bs"}, "method": "select"}

    document = http.download_html(url=url)
    soup = BeautifulSoup(document, "lxml")
    tags = soup.select(selector="div#zb > div.xh")
    jokes = list()
    for tag in tags:
        joke = JokeFields()
        joke.title = get_tag_attribute(tag, title_config, "text")
        joke.text = get_tag_attribute(tag, text_config, "text")
        joke.n_like = get_tag_attribute_int(tag, like_config, "text")
        joke.n_dislike = get_tag_attribute_int(tag, dislike_config, "text")
        joke.publish_ori_name = get_tag_attribute(tag, user_config, "text")
        jokes.append(joke)
    return jokes


def joke_budejie_parser(url):
    text_config = {"params": {"selector": "div.j-r-list-c-desc > a"}, "method": "select"}
    user_config = {"params": {"selector": "img.u-logo"}, "method": "select"}
    user_icon_config = {"params": {"selector": "img.u-logo"}, "method": "select"}
    like_config = {"params": {"selector": "li.j-r-list-tool-l-up"}, "method": "select"}
    dislike_config = {"params": {"selector": "li.j-r-list-tool-l-down"}, "method": "select"}
    comment_config = {"params": {"selector": "li.j-comment"}, "method": "select"}
    pb_time_config = {"params": {"selector": "span.u-time"}, "method": "select"}
    repost_config = {"params": {"selector": "div.j-r-list-tool-ct-share-c"}, "method": "select"}
    document = http.download_html(url=url)
    soup = BeautifulSoup(document, "lxml")
    tags = soup.select(selector="div.j-r-list > ul > li")
    jokes = list()
    for tag in tags:
        joke = JokeFields()
        joke.publish_ori_name = get_tag_attribute(tag, user_config, "alt")
        joke.publish_ori_icon = get_tag_attribute(tag, user_icon_config, "data-original")
        joke.text = get_tag_attribute(tag, text_config, "text")
        joke.n_like = get_tag_attribute_int(tag, like_config, "text")
        joke.n_dislike = get_tag_attribute_int(tag, dislike_config, "text")
        pb_time = get_tag_attribute(tag, pb_time_config, "text")
        joke.publish_time = format_datetime_string(pb_time)
        joke.n_repost = get_tag_attribute_int(tag, repost_config, "text")
        joke.n_comment = get_tag_attribute_int(tag, comment_config, "text")
        jokes.append(joke)
    return jokes


def joke_caoegg_parser(url):
    text_config = {"params": {"selector": "div.c > a > span"}, "method": "select"}
    like_config = {"params": {"selector": "div#dateright span.voteyes > font"}, "method": "select"}
    dislike_config = {"params": {"selector": "div#dateright span.voteno > font"}, "method": "select"}
    pb_time_config = {"params": {"selector": "div#dateright"}, "method": "select"}
    document = http.download_html(url=url)
    soup = BeautifulSoup(document, "lxml")
    tags = soup.select(selector="div#wrap_info > div.infobox")
    jokes = list()
    for tag in tags:
        joke = JokeFields()
        joke.text = get_tag_attribute(tag, text_config, "text")
        joke.text = joke.text.strip("What a fucking day!")
        joke.n_like = get_tag_attribute_int(tag, like_config, "text")
        joke.n_dislike = get_tag_attribute_int(tag, dislike_config, "text")
        pb_time = get_tag_attribute(tag, pb_time_config, "text")
        joke.publish_time = format_datetime_string(pb_time)
        jokes.append(joke)
    return jokes


def joke_duanzidao_parser(url):
    text_config = {"params": {"selector": "div.article"}, "method": "select"}
    user_config = {"params": {"selector": "table.author td > ul > li > a"}, "method": "select"}
    user_icon_config = {"params": {"selector": "td.avatar img"}, "method": "select"}
    like_config = {"params": {"selector": "em.good-btn > span"}, "method": "select"}
    dislike_config = {"params": {"selector": "em.bad-btn > span"}, "method": "select"}
    pb_time_config = {"params": {"selector": "table"}, "method": "select"}
    document = http.download_html(url=url)
    soup = BeautifulSoup(document, "lxml")
    tags = soup.select(selector="div#main > div.panel")
    jokes = list()
    for tag in tags:
        joke = JokeFields()
        joke.publish_ori_name = get_tag_attribute(tag, user_config, "text")
        joke.publish_ori_icon = get_tag_attribute(tag, user_icon_config, "src")
        joke.text = get_tag_attribute(tag, text_config, "text")
        joke.n_like = get_tag_attribute_int(tag, like_config, "text")
        joke.n_dislike = get_tag_attribute_int(tag, dislike_config, "text")
        pb_time = get_tag_attribute(tag, pb_time_config, "text")
        joke.publish_time = format_datetime_string(pb_time)
        jokes.append(joke)
    return jokes


def joke_helegehe_parser(url):
    text_config = {"params": {"selector": "a.contentHerf"}, "method": "select"}
    user_config = {"params": {"selector": "h2"}, "method": "select"}
    user_icon_config = {"params": {"selector": "img"}, "method": "select"}
    like_config = {"params": {"selector": "a.output-leftSupport"}, "method": "select"}
    dislike_config = {"params": {"selector": "a.output-leftOpposition"}, "method": "select"}
    pb_time_config = {"params": {"selector": "div.publishedIn"}, "method": "select"}
    document = http.download_html(url=url)
    soup = BeautifulSoup(document, "lxml")
    tags = soup.select(selector="article.post")
    jokes = list()
    for tag in tags:
        joke = JokeFields()
        joke.publish_ori_name = get_tag_attribute(tag, user_config, "text")
        joke.publish_ori_icon = get_tag_attribute(tag, user_icon_config, "src")
        joke.text = get_tag_attribute(tag, text_config, "text")
        joke.n_like = get_tag_attribute_int(tag, like_config, "text")
        joke.n_dislike = get_tag_attribute_int(tag, dislike_config, "text")
        pb_time = get_tag_attribute(tag, pb_time_config, "text")
        joke.publish_time = format_datetime_string(pb_time)
        jokes.append(joke)
    return jokes


def joke_khdx_parser(url):
    text_config = {"params": {"selector": "dd.content"}, "method": "select"}
    user_config = {"params": {"selector": "p.user > a"}, "method": "select"}
    user_icon_config = {"params": {"selector": "img"}, "method": "select"}
    like_config = {"params": {"selector": "a.ding > div > i"}, "method": "select"}
    dislike_config = {"params": {"selector": "a.cai > div > i"}, "method": "select"}
    pb_time_config = {"params": {"selector": "span.fr"}, "method": "select"}
    document = http.download_html(url=url)
    soup = BeautifulSoup(document, "lxml")
    tags = soup.select(selector="dl.main-list")
    jokes = list()
    for tag in tags:
        joke = JokeFields()
        joke.publish_ori_name = get_tag_attribute(tag, user_config, "text")
        joke.publish_ori_icon = get_tag_attribute(tag, user_icon_config, "src")
        joke.publish_ori_icon = urljoin(url, joke.publish_ori_icon)
        joke.text = get_tag_attribute(tag, text_config, "text")
        joke.n_like = get_tag_attribute_int(tag, like_config, "text")
        joke.n_dislike = get_tag_attribute_int(tag, dislike_config, "text")
        pb_time = get_tag_attribute(tag, pb_time_config, "text")
        joke.publish_time = format_datetime_string(pb_time)
        jokes.append(joke)
    return jokes
