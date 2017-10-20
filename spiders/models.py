# coding: utf-8

from .utilities import utc_datetime_now

__author__ = "lixianyang"
__email__ = "705834854@qq.com"
__date__ = "2017-05-17 14:47"


class Base(object):

    def to_dict(self):
        return dict(self.__dict__)

    @classmethod
    def from_dict(cls, d):
        self = cls()
        for k, v in d.items():
            self.__dict__[k] = v
        return self


class BaseImageMeta(Base):

    def __init__(self):
        self.src = ""
        self.width = 0
        self.height = 0


class ImageMeta(BaseImageMeta):

    def __init__(self):
        super(ImageMeta, self).__init__()
        self.org = ""
        self.qr = False
        self.gray = False
        self.md5 = ""


class FeedImageMeta(BaseImageMeta):

    def __init__(self):
        super(FeedImageMeta, self).__init__()


class ListFields(Base):
    """ 列表页解析获得的一些字段 """

    def __init__(self):
        self.url = ""  # 详情页链接
        self.title = ""  # 标题
        self.publish_time = ""  # 发布时间
        self.publish_ori_name = ""  # 发布源
        self.abstract = ""  # 摘要
        self.tags = ""  # 标签
        self.comment = dict()  # 评论评论需要的字段
        self.html = ""  # 列表页可能获取到 html
        self.thumbs = list()  # 列表页缩略图

    def to_dict(self):
        return {k: v for k, v in self.__dict__.items() if v}


class BaseFields(Base):

    def __init__(self):
        self.publish_time = ""  # 默认为空的字符串
        self.publish_ori_name = ""  # 发布的源(源作者或源网站)
        self.publish_ori_url = ""  # 原链接
        self.publish_ori_icon = ""  # 发布源的图标
        self.tags = ""  # 文章标签
        self.comment = dict()  # 评论抓取需要的字段

        self.n_read = 0  # 阅读量或播放量
        self.n_comment = 0  # 评论量
        self.n_like = 0  # 喜欢/赞
        self.n_dislike = 0  # 不喜欢/踩
        self.n_repost = 0  # 转发

    def to_dict(self):
        return dict(self.__dict__)

    def show(self):
        for k, v in self.__dict__.items():
            print k, ":", v
        print "*" * 120


class NewsFields(BaseFields):

    def __init__(self):
        super(NewsFields, self).__init__()
        self.title = ""
        self.abstract = ""  # 新闻的摘要
        self.content = list()  # 新闻的内容
        self.original = False  # 是否是抓取源原创的新闻
        self.ori_feeds = list()  # 原始列表页图片链接
        self.gen_feeds = list()  # 智能选择生成列表页图
        self.n_images = 0
        self.n_videos = 0
        self.n_audios = 0


class VideoFields(BaseFields):

    def __init__(self):
        super(VideoFields, self).__init__()
        self.title = ""  # 标题
        self.format = ""  # 视频格式
        self.src = ""  # 视频链接
        self.thumbnail = ""  # 缩略图
        self.duration = 0  # 时长
        self.description = ""  # 视频描述


class JokeFields(BaseFields):
    def __init__(self):
        super(JokeFields, self).__init__()
        self.text = ""  # 段子内容
        self.title = ""  # 标题(可以为空)


class AtlasFields(NewsFields):  # 和新闻格式相同，content格式不同

    def __init__(self):
        super(AtlasFields, self).__init__()
        del self.n_videos
        del self.n_audios


class PictureFields(BaseFields):

    def __init__(self):
        super(PictureFields, self).__init__()


class ForeignFields(Base):

    def __init__(self):
        super(ForeignFields, self).__init__()
        self.site = ""
        self.channel = ""
        self.config = ""
        self.request = ""
        self.category1 = ""
        self.category2 = ""
        self.priority = 0
        self.time = utc_datetime_now()
