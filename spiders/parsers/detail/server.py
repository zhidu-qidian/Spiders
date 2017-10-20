# coding: utf-8

"""详情页解析"""

import json
import os
import types
from urlparse import urlparse

from extractor import MAPPING
from download import download_page

__author__ = "Sven Lee"
__copyright__ = "Copyright 2016-201, ShangHai Lie Ying"
__license__ = "Private"
__email__ = "lee1300394324@gmail.com"
__date__ = "2016-10-26 16:22"


class Formatter(object):
    """格式化功能类"""

    @classmethod
    def format_domain(cls, domain):
        """点分域名为逆序tuple
        :param domain:域名
        :type domain:str
        :return:格式化的域名
        :rtype:tuple
        """
        domain = domain.split(".")
        domain.reverse()
        return tuple(domain)

    @classmethod
    def format_path_domain(cls, match):
        """统一配置文件match中带path的key和不带path的key为(path, domain, value)

        输入: match = {"qq.com":["2", "3"], "qq.com/news": ["1"]}
        返回: {(None, ("com","qq")):["2", "3"], (/news, ("com","qq")):["1"]}
        :param match:配置文件中的match字段的值
        :type match:dict
        :return:统一后的值
        :rtype:dict
        """
        result = dict()
        for key, value in match.items():
            index = key.find("/")
            if index < 0:
                path = None
                domain = key
            else:
                path = key[index:]
                domain = key[:index]
            result[(path, Formatter.format_domain(domain))] = value
        return result

    @classmethod
    def format_result(cls, **kwargs):
        """格式化解析结果 missing 字段表示该解析不完整,缺失已知字段

        kwargs keys: title, date, source, author, editor, summary, tags, content
        """
        keys = ["title", "date", "source", "author", "editor", "summary",
                "tags"]
        result = dict.fromkeys(keys)
        for key in result:
            result[key] = kwargs.get(key, "")
        content = kwargs.get("content", None)
        result["missing"] = kwargs.get("missing", False)
        result["content"] = content if content else list()
        return result


class Configer(object):
    """配置功能类"""

    @classmethod
    def get_files_in_dir(cls, directory, suffix=".json"):
        """递归获取指定文件夹下的以suffix为后缀的文件路径
        :param directory:文件夹路径
        :type directory:str
        :param suffix:后缀,默认".json"
        :type suffix:str
        :return:文件路径列表
        :rtype:list
        """
        files = list()
        for dir_path, _, file_names in os.walk(directory):
            for name in file_names:
                if name.endswith(suffix) and not name.startswith("_"):
                    files.append(os.path.join(dir_path, name))
        return files

    @classmethod
    def load_json_configs(cls, paths):
        """加载并解析配置文件
        :param paths:配置文件路径列表
        :type paths:list
        :return:一般配置,外链配置
        :rtype:tuple
        """
        configs, outers = dict(), dict()
        for path in paths:
            c, o = cls.load_json_config(path)
            configs.update(c)
            outers.update(o)
        return configs, outers

    @classmethod
    def load_json_config(cls, path):
        """加载配置文件并解析,返回一般配置字典和外链配置字典
        :param path:配置文件路径
        :type path:str
        :return:格式化后的配置文件
        :rtype:tuple
        """
        configs, outers = dict(), dict()
        with open(path) as f:
            try:
                config = json.load(f)
            except Exception:
                pass  # load json config fail
            else:
                configs, outers = cls.parse_json_config(config)
        return configs, outers

    @classmethod
    def parse_json_config(cls, config):
        """解析配置,返回一般配置字典和外链配置字典

        主要格式化domain和path domain
        输入:{"qq.com":{
                        "configs":{"1":config1, "2":config2},
                        "match":{"qq.com":["1"]},
                        "outer":{"hello":["2"]}
                        }
            }
        输出:
            configs={("com","qq"):{"configs":{"1":config1, "2":config2},
                                    "match":{(None,("com","qq")):["1"]},
                                    "outer":{"hello":["2"]}}}
            outers={"hello":config2}
        :param config:配置
        :type config:dict
        :return:格式化后的配置
        :rtype:tuple
        """
        configs, outers = dict(), dict()
        for domain, value in config.items():
            domain = Formatter.format_domain(domain)
            if "match" in value:
                value["match"] = Formatter.format_path_domain(value["match"])
                configs[domain] = value
            if "outer" in value:
                for k, v in value["outer"].items():
                    outers[k] = [value["configs"][key] for key in v]
        return configs, outers

    @classmethod
    def get_default_config_directory(cls):
        """获取默认的配置文件目录
        :return:配置文件目录
        :rtype:str
        """
        directory = os.path.split(os.path.realpath(__file__))[0]
        return os.sep.join([directory, "configs"])

    @classmethod
    def load_configs(cls, directory=None):
        """加载解析指定目录下的配置文件,若不指定则加载默认配置
        :param directory:指定的配置文件夹
        :type directory:str, default=None
        :return:一般配置和外链配置
        :rtype:tuple
        """
        if directory is None:
            directory = cls.get_default_config_directory()
        paths = cls.get_files_in_dir(directory)
        configs, outers = cls.load_json_configs(paths)
        return configs, outers


class Matcher(object):
    """匹配功能类"""

    @classmethod
    def domain_match(cls, d1, d2):
        """格式化的域名匹配,相当于d1.startswith(d2)
        :param d1:待匹配的域名
        :type d1:tuple
        :param d2:配置中的域名
        :type d2:tuple
        :return:是否匹配
        :rtype:bool
        """
        if len(d2) > len(d1):
            return False
        for i, item in enumerate(d2):
            if item != d1[i]:
                return False
        return True

    @classmethod
    def path_match(cls, path, pattern):
        """格式化的路径匹配,默认从头匹配,若pattern最后一个字符为$,则从末尾匹配
        :param path:待匹配的路径
        :type path:str
        :param pattern:配置中的路径格式
        :type pattern:str
        :return:是否匹配
        :rtype:bool
        """
        if pattern.endswith("$"):
            if path.endswith(pattern[:-1]):
                return True
        else:
            if path.startswith(pattern):
                return True
        return False

    @classmethod
    def is_outer_link(cls, url_obj, keywords):
        """判断 url 的 path,params,query 部分是否包含指定的关键字
        :param url_obj:url 解析对象
        :type url_obj:urlparse.ParseResult
        :param keywords:关键字列表
        :type keywords:str or list of str
        :return:是否外链
        :rtype:bool
        """
        path, params, query = url_obj[2:5]
        if isinstance(keywords, types.StringTypes):
            keywords = [keywords]
        for word in keywords:
            if word in path or word in query or word in params:
                return True
        return False

    @classmethod
    def outer_match(cls, url_obj, outers):
        """外链匹配
        :param url_obj:url解析对象
        :type url_obj:urlparse.ParseResult
        :param outers:外链配置
        :type outers:dict
        :return:匹配的配置
        :rtype:list
        """
        for k, v in outers.items():
            if cls.is_outer_link(url_obj, k):
                return v
        return []

    @classmethod
    def normal_match(cls, url_obj, configs):
        """一般匹配
        :param url_obj:url解析对象
        :type url_obj:urlparse.ParseResult
        :param configs:一般配置
        :type configs:dict
        :return:匹配的配置
        :rtype:list
        """
        domain, path = url_obj[1:3]
        domain = Formatter.format_domain(domain)
        config = None
        for key in configs.keys():
            if cls.domain_match(domain, key):
                config = configs[key]
                break
        if config is None:
            return []  # domain not support
        p_match = list()
        n_match = list()
        for key in config["match"].keys():
            p, d = key
            if p is None:
                if cls.domain_match(domain, d):
                    n_match.append((d, config["match"][key]))
            else:
                if cls.path_match(path, p) and cls.domain_match(domain, d):
                    p_match.append((d, config["match"][key]))
        lencmp = lambda item: len(item[0])
        n_match.sort(key=lencmp, reverse=True)
        p_match.sort(key=lencmp, reverse=True)
        keys = list()
        for d, k in p_match+n_match:
            keys.extend(k)
        return [config["configs"][k] for k in keys]

    @classmethod
    def match(cls, url, configs=None, outers=None):
        """获取与url匹配的所有解析配置,匹配程度递减
        :param url:网址
        :type url:str
        :param configs:一般配置
        :type configs:dict
        :param outers:外链配置
        :type outers:dict
        :return:匹配的解析配置
        :rtype:list
        """
        matches = list()
        url_obj = urlparse(url)
        if outers:
            matches.extend(cls.outer_match(url_obj, outers))
        if configs:
            matches.extend(cls.normal_match(url_obj, configs))
        return matches


class Displayer(object):
    """显示功能类"""

    @classmethod
    def display_result(cls, result):

        def _get_attributes(tag):
            _attributes = ""
            for key, value in tag.items():
                if key in ["tag", "text"]:
                    continue
                _attributes += " {key}='{value}' ".format(key=key, value=value)
            return _attributes

        strings = list()
        strings.append("title: %s" % result.get("title"))
        strings.append("publish time: %s" % result.get("date"))
        strings.append("publish site: %s" % result.get("source"))
        strings.append("missing: %s" % result.get("missing"))
        strings.append("author: %s" % result.get("author"))
        strings.append("content:")
        for item in result["content"]:
            attributes = _get_attributes(item)
            if item["tag"] == "p":
                strings.append(u"<p>{text}</p>".format(text=item.get("text")))
            elif item["tag"] == "img":
                strings.append(u"<img{}>".format(attributes))
            else:
                text = item.get("text")
                if not text:
                    text = ""
                strings.append(
                    u"<{0}{1}>{2}</{0}>".format(item["tag"], attributes, text))
        print("*"*80)
        print(os.linesep.join(strings))


class Parser(object):
    """解析功能类"""

    @classmethod
    def extract(cls, url, document, config):
        """根据配置抽取内容
        :param url:网址
        :type url:str
        :param document:网址的内容
        :type document:str
        :param config:配置
        :type config:dict
        :return:抽取的数据
        :rtype:dict
        """
        extractor_key = config.get("extractor")
        if not extractor_key:
            extractor_key = "default"
        ext = MAPPING[extractor_key](document, url)
        title = ext.extract_title(config.get("title"))
        date = ext.extract_date(config.get("date"))
        source = ext.extract_source(config.get("source"))
        author = ext.extract_author(config.get("author"))
        editor = ext.extract_editor(config.get("editor"))
        summary = ext.extract_summary(config.get("summary"))
        tags = ext.extract_tags(config.get("tags"))
        if hasattr(ext, "judge_missing"):
            missing = ext.judge_missing(config.get("missing"))
        else:
            missing = False
        content = ext.extract_content(
            param=config.get("content"),
            clean=config.get("clean"),
            before=config.get("before"),
            after=config.get("after")
        )
        return Formatter.format_result(title=title, date=date, source=source,
                                       author=author, editor=editor,
                                       summary=summary, tags=tags,
                                       content=content, missing=missing)

    @classmethod
    def parsing(cls, url, configs=None, outers=None, document=None, check=None):
        """解析接口
        :param url:网址
        :type url:str
        :param configs:一般配置
        :type configs:dict
        :param outers:外链配置
        :type outers:dict
        :param document:网址的内容
        :type document:str
        :param check:要检测的字段,若没有抽取到该字段,则返回空的结果
        :type check:list
        :return:是否有可用的域名配置(bool)，返回的解析结果(dict)
        :rtype: bool, dict
        """
        if check is None:
            check = ["content"]
        if not document:
            document = download_page(url)
        flag = False
        for config in Matcher.match(url, configs=configs, outers=outers):
            flag = True
            result = cls.extract(url, document, config)
            if all([result[field] for field in check]):
                return flag, result
        return flag, Formatter.format_result()


class DefaultParser(object):

    def __init__(self):
        cfgs, ots = Configer.load_configs()
        self.cfgs = cfgs
        self.ots = ots

    def __call__(self, url, document=None, check=None):
        flag, result = Parser.parsing(
            url, self.cfgs, self.ots, document=document, check=check
        )
        result["support"] = flag
        return result


def main():
    import sys
    cfgs, ots = Configer.load_configs()
    _url = sys.argv[1].strip()
    _document = None
    if len(sys.argv) > 2:
        _name = sys.argv[2].strip()
        with open(_name) as f:
            _document = f.read()
    flag, article = Parser.parsing(_url, cfgs, ots, document=_document)
    if not flag:
        print("not support this domain: %s" % _url)
    Displayer.display_result(article)


if __name__ == "__main__":
    main()
