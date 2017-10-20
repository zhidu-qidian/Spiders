# coding:utf-8

""" HTML提取工具函数 """

from urlparse import urljoin
from bs4 import Tag, BeautifulSoup


def find_tag(root, param):
    """
    根据参数和节点，返回该节点下满足条件的子节点

    支持 bs4 中的 find, find_all 和 select 三种定位方式, method 参数表示要使用的定位方法,
    默认为 find, params 为调用的参数, method(**params), nth 参数表示找到的第几个 Tag,
    默认为 0. 例如：
    {"method": "find_all", "params": {"id": "article"}, "nth": 0}
    :param root:根节点
    :type root:Tag or BeautifulSoup
    :param param:检索参数
    :type param:dict
    :return:找到的 tag 或者 None
    :rtype: Tag or None
    """
    if not isinstance(root, (Tag, BeautifulSoup)):
        return None
    method = param.get("method", "find")
    params = param["params"]
    nth = param.get("nth", 0)
    if method == "find":
        tag = root.find(**params)
        return tag
    elif method == "find_all":
        tags = root.find_all(**params)
    elif method == "select":
        tags = root.select(**params)
    else:
        raise ValueError("param['method'] only support find, find_all and select")
    return tags[nth] if len(tags) > nth else None


def find_tags(root, param):
    """
    根据参数和节点，返回该节点下满足条件的所有子节点

    支持 bs4 中的 find, find_all 和 select 三种定位方式, method 参数表示要使用的定位方法,
    默认为 find_all, params 为调用的参数, method(**params). 例如：
    {"method": "find_all", "params": {"id": "article"}}
    :param root:根节点
    :type root:Tag or BeautifulSoup
    :param param:检索参数
    :type param:dict
    :return:找到的 tags
    :rtype: list
    """
    if not isinstance(root, (Tag, BeautifulSoup)):
        return []
    method = param.get("method", "find_all")
    params = param["params"]
    if method == "find":
        tag = root.find(**params)
        if tag is None:
            return []
        else:
            return [tag]
    elif method == "find_all":
        tags = root.find_all(**params)
    elif method == "select":
        tags = root.select(**params)
    else:
        raise ValueError("param['method'] only support find, find_all and select")
    return tags


def absolute_links(root, url):
    """
    a 标签中的相对地址都改为绝对地址
    :param root:要改变的根节点
    :type root:Tag or BeautifulSoup
    :param url:基础链接
    :type url:str
    :return:无返回值
    :rtype:
    """
    assert isinstance(root, (Tag, BeautifulSoup))
    if url:
        for item in root.find_all("a"):
            item.attrs["href"] = urljoin(url, item.get("href", ""))


def extract_tag_attribute(root, name="text"):
    """
    抽取节点的属性,text属性为节点中的text
    :param root:要抽取的节点
    :type root:Tag or BeautifulSoup
    :param name:要获取的属性
    :type name:str
    :return:属性值,若属性值返回的是列表,则通过','拼接列表
    :rtype:str
    """
    if root is None:
        return ""
    assert isinstance(root, (Tag, BeautifulSoup))
    if name == "text":
        return root.get_text().strip()
    else:
        value = root.get(name, "")
        if isinstance(value, (list, tuple)):
            return ",".join(value)
        else:
            return value.strip()


def unwrap_child_tags(root, names):
    """

    :param root:
    :param names:
    :return:
    """
    for name in names:
        child = getattr(root, name)
        while child:
            child.unwrap()
            child = getattr(root, name)


def get_tag_attribute(root, param, attribute="text"):
    """ 查找并抽取标签属性 """
    if param.get("params"):
        root = find_tag(root=root, param=param)
    return "" if root is None else extract_tag_attribute(root, name=attribute)
