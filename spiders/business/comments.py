# coding: utf-8

__author__ = "lixianyang"
__email__ = "705834854@qq.com"
__date__ = "2017-05-24 10:56"


def g_kuaibao_comment_params(_id):
    # return "http://r.cnews.qq.com/getQQNewsComment/" \
    #        "?comment_id={_id}&page=1".format(_id=_id)
    return {"id": _id}


def g_news163_comment_params(_id):
    # return "http://comment.api.163.com/api/v1/products/" \
    #        "a2869674571f77b5a0867c3d71db5856/threads/{_id}" \
    #        "/app/comments/newList?offset=0&limit=40".format(_id=_id)
    return {"id": _id}


def g_weixin_comment_params(news_url):
    news_prefix = "http://mp.weixin.qq.com/s"
    comment_prefix = "http://mp.weixin.qq.com/mp/getcomment"
    if not news_url.startswith(news_prefix):
        return dict()
    else:
        return {"url": news_url.replace(news_prefix, comment_prefix)}


def g_weibo_comment_params(_id):
    # return "https://api.weibo.com/2/comments/show.json?" \
    #         "access_token=2.004t5RdC0hJy9lac6c22897742owGD" \
    #         "&id={_id}&count=50&page=1".format(_id=_id)
    return {"id": _id}


def get_comment_url(site, *args, **kwargs):
    if site == "57b2c182da083a1c19957b1e":
        return g_kuaibao_comment_params(*args, **kwargs)
    elif site == "57736f7c1100840aa214dbee":
        return g_news163_comment_params(*args, **kwargs)
    elif site == "57bab42eda083a1c19957b1f":
        return g_weixin_comment_params(*args, **kwargs)
    elif site == "583bc5155d272cd5c47a7668":
        return g_weibo_comment_params(*args, **kwargs)
    else:
        return dict()
