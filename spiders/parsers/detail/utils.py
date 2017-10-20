# coding: utf-8

"""常用工具函数"""

from datetime import datetime
from importlib import import_module
import os
import re

__author__ = "Sven Lee"
__copyright__ = "Copyright 2016-2019, ShangHai Lie Ying"
__credits__ = ["Sven Lee"]
__license__ = "Private"
__version__ = "1.0.0"
__email__ = "lee1300394324@gmail.com"
__date__ = "2016-05-10 17:16"


def load_object(path):
    """Load an object given its absolute object path, and return it.

    object can be a class, function, variable or instance.
    path ie: 'newsextractor.config.163_com.urls.URLS'
    """

    try:
        dot = path.rindex('.')
    except ValueError:
        raise ValueError("Error loading object '%s': not a full path" % path)

    module, name = path[:dot], path[dot + 1:]
    mod = import_module(module)

    try:
        obj = getattr(mod, name)
    except AttributeError:
        raise NameError("Module '%s' doesn't define any object named '%s'" % (module, name))

    return obj


def get_subdir_names(path):
    """获取文件夹下的所有子文件夹的完整路径

    :param path:要获取的文件夹路径
    :type path:str
    :return:子文件夹列表
    :rtype:list
    """
    names = list()
    files = os.listdir(path)
    for f in files:
        p = os.path.join(path, f)
        if os.path.isdir(p):
            names.append(p)
    return names


def has_filename_in_path(path, filename):
    """判断指定文件夹下是否包含特定文件名

    :param path:文件夹路径
    :type path:str
    :param filename:文件名
    :type filename:str
    :return:是否包含
    :rtype:bool
    """
    for f in os.listdir(path):
        if f == filename:
            return True
    return False


def load_object_default(path, default=None):
    """Load an object given its absolute object path, and return it.

    object can be a class, function, variable or instance. if no abject in path,
    default will be returned.
    :param path:路径
    :type path:str
    :param default:默认对象
    :type default:None, list, dict, class, function, variable, instance
    :return:load object
    :rtype:class, function, variable, instance
    """
    try:
        obj = load_object(path)
    except NameError:
        obj = default
    return obj


def clean_date_time(string):
    """清洗时间

    :param string: 包含要清洗时间的字符串
    :type string: str or unicode
    :return: 生成的字符串, 格式为 2016-02-01 12:01:59
    :rtype: str
    """
    if isinstance(string, str):
        string = string.decode("utf-8")
    date_time_string = ""
    if string.isdigit():
        length = len(string)
        timestamp = int(string)
        if length == 13:
            timestamp /= 1000
            length -= 3
        if length == 10:
            date_time = datetime.fromtimestamp(timestamp)
            return date_time.strftime("%Y-%m-%d %H:%M:%S")
    p_date_list = [
        u"((20\d{2})[/\.-])(\d{1,2})[/\.-](\d{1,2})",
        u"((20\d{2})年)(\d{1,2})月(\d{1,2})",
        u"((\d{2})[/\.-])(\d{1,2})[/\.-](\d{1,2})",
        u"((20\d{2})[/\.-])?(\d{1,2})[/\.-](\d{1,2})",
        u"((20\d{2})年)?(\d{1,2})月(\d{1,2})",
    ]
    for p_date in p_date_list:
        date_match = re.search(p_date, string)
        if date_match is not None:
            break
    else:
        return date_time_string
    p_time = r"(\d{1,2}):(\d{1,2})(:(\d{1,2}))?"
    time_match = re.search(p_time, string)
    now = datetime.now()
    year_now = now.strftime("%Y")
    hour_now = now.strftime("%H")
    minute_now = now.strftime("%M")
    second_now = now.strftime("%S")
    if date_match is None:
        return date_time_string
    else:
        date_groups = date_match.groups()
    if time_match is None:
        time_groups = (hour_now, minute_now, ":" + second_now, second_now)
    else:
        time_groups = time_match.groups()
    year = date_groups[1]
    month = date_groups[2]
    if len(month) == 1:
        month = "0" + month
    day = date_groups[3]
    if len(day) == 1:
        day = "0" + day
    hour = time_groups[0]
    minute = time_groups[1]
    second = time_groups[3]
    if year is None:
        year = year_now
    if second is None:
        second = second_now
    if len(year) == 2:
        year = "20" + year
    date_string = "-".join([year, month, day])
    time_string = ":".join([hour, minute, second])
    date_time_string = date_string + " " + time_string
    return date_time_string


def parse_js(expr):
    """
    解析非标准JSON的Javascript字符串，等同于json.loads(JSON str)
    :param expr:非标准JSON的Javascript字符串
    :return:Python字典
    """
    import ast
    main_body = ast.parse(expr)
    if len(main_body.body) < 1:
        return []
    item = main_body.body[0]

    def parse(node):
        """
        通过抽象语法树（AST）表进行映射转换
        :param node:
        :return:
        """
        if isinstance(node, ast.Expr):
            return parse(node.value)
        elif isinstance(node, ast.Num):
            return node.n
        elif isinstance(node, ast.Str):
            return node.s
        elif isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Dict):
            return dict(zip(map(parse, node.keys), map(parse, node.values)))
        elif isinstance(node, ast.List):
            return map(parse, node.elts)
        else:
            raise NotImplementedError(node.__class__)

    return parse(item)


if __name__ == "__main__":
    print clean_date_time(u"2017/05/04 15:22:00")
    print clean_date_time(u"2017-5-4 15:22:00")
    print clean_date_time(u"2017年5月4日 15:22")
    print clean_date_time("05月4日")
    print clean_date_time(u"05-04 15:22:00")
    print clean_date_time(u"2017.05.04 15:22:00")
    print clean_date_time("05/4")
