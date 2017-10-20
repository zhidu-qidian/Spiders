# coding: utf-8

""" 列表页解析结果数据结构 """


class Base(object):

    def to_dict(self):
        return dict(self.__dict__)

    @classmethod
    def from_dict(cls, dictionary):
        assert isinstance(dictionary, dict)
        self = cls()
        self.__dict__.update(dictionary)
        return self


class Fields(Base):
    """ 列表页解析结果结构

    names: 可配置解析并返回解析结果的字段
    """
    names = ["url", "title", "publish_time", "publish_site", "author",
             "abstract", "keywords", "comment_id", "html", "thumb"]

    def __init__(self):
        for name in self.names:
            self.__dict__[name] = ""

    def is_valid(self):
        if self.__dict__.get("title") and self.__dict__.get("url"):
            return True
        else:
            return False
