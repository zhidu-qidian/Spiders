# coding: utf-8

"""html下载"""

import requests
from w3lib.encoding import html_to_unicode

__author__ = "Sven Lee"
__copyright__ = "Copyright 2016-2019, ShangHai Lie Ying"
__credits__ = ["Sven Lee"]
__license__ = "Private"
__version__ = "1.0.0"
__email__ = "lee1300394324@gmail.com"
__date__ = "2016-05-10 17:04"


def download_page(url):
    """下载html页面
    :param url:网址
    :type url:str
    :return:下载的html
    :rtype:str
    """
    headers = {
        "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/50.0.2661.86 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        _, content = html_to_unicode(
            content_type_header=response.headers.get("content-type"),
            html_body_str=response.content
        )
        return content.encode("utf-8")
    else:
        return ""
