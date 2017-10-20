# coding: utf-8

__author__ = "lixianyang"
__email__ = "705834854@qq.com"
__date__ = "2017-05-18 15:40"


class Error(Exception):
    pass


class NotSupportError(Error):

    pass


class MissFieldError(Error):

    pass


class ImageError(Error):

    pass


class ImageDownloadError(ImageError):

    pass


class ImageUploadError(ImageError):

    pass
