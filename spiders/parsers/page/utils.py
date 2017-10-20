# coding: utf-8
"""
工具函数
"""
import json
import os
import re
from datetime import datetime


def load_json_file(path):
    obj = dict()
    with open(path) as f:
        try:
            obj = json.load(f)
        except Exception as e:
            try:
                obj = eval(f.read(), type('Dummy', (dict,),
                                          dict(__getitem__=lambda s, n: n))())
            except Exception as e:
                print e.message
    return obj


def get_path_files(path):
    """递归获取指定路径下的文件"""
    names = list()
    for dir_path, dir_names, file_names in os.walk(path):
        for f in file_names:
            if f.endswith(".json") and not f.startswith("_"):
                names.append(os.path.join(dir_path, f))
    return names


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
    pass
