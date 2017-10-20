# coding: utf-8

""" 图片处理 """

from datetime import datetime
from hashlib import sha256, md5
import logging
import math
from StringIO import StringIO

from PIL import Image
import zbarlight

from spiders.alioss import OnlineImageUploader
from spiders.error import ImageDownloadError
from spiders.models import ImageMeta, FeedImageMeta
from spiders.utilities import http


def upload_image(data, uploader):
    """ 上传图片到阿里云 oss

    Notice: gif 图只能上传最原始的数据, Pillow.Image.Image 只保存第一帧

    :param data: 原始数据
    :type data: str
    :return: oss 的链接
    :rtype: str
    """
    o_image = Image.open(StringIO(data))
    w, h = o_image.width, o_image.height
    name = sha256(o_image.tobytes()).hexdigest()
    o_format = o_image.format.lower()
    if o_format == "gif":
        content_type = "image/gif"
        suffix = "gif"
    else:
        format = "jpeg"
        if o_image.mode != "RGBA":
            o_image = o_image.convert("RGBA")
        bf = StringIO()
        o_image.save(bf, format=format, quality=95)  # 统一转换为 jpeg
        data = bf.getvalue()
        bf.close()
        content_type = "image/jpeg"
        suffix = "jpg"
    prefix = datetime.now().strftime("%Y%m%d%H%M%S")
    full_name = "%s%s_%sX%s.%s" % (prefix, name, w, h, suffix)
    headers = {"content-type": content_type}
    url = uploader.upload(data=data, name=full_name, headers=headers)
    return url


def get_image_metas(image):
    """ 获取该图片的一些属性

    :param image: 输入图像
    :type image: PIL.Image.Image
    :return: 长, 宽, 是否是二维码, 是否偏灰度图
    :rtype: (int, int, bool, bool)
    """
    w, h = image.width, image.height
    qr = ZbarScanner.is_qr_code(image)
    gray = image.convert("L")
    is_gray = grayness(gray)
    return w, h, qr, is_gray


def grayness(gray):
    """  判断图像是否是灰度图像 
    
    :param gray: 要判断的单通道图像
    :type gray: PIL.Image.Image
    :return: 灰度图: True, 不是灰度图: False
    :rtype: bool
    """
    RATIO = 0.75
    BLACK = 50
    WHITE = 200
    black, white = 0, 0
    for w in range(gray.width):
        for h in range(gray.height):
            pixel = gray.getpixel((w, h))
            if pixel > WHITE:
                white += 1
            elif pixel < BLACK:
                black += 1
    points = gray.width * gray.height
    return black*1.0/points >= RATIO or white*1.0/points >= RATIO


def get_feed_size(width, height):
    """ 根据 4:3 的比例获取适当的 feed 图尺寸 """
    ratio = 4.0/3
    _w, _h = 0, 0
    for w in range(width, 159, -1):
        for h in range(height, 119, -1):
            r = w*1.0/h
            if r == ratio:
                _w, _h = w, h
                break
            elif r > ratio:
                break
        if _w != 0:
            break
    return _w, _h


class ZbarScanner(object):

    @classmethod
    def scan(cls, image):
        return zbarlight.scan_codes("qrcode", image)

    @classmethod
    def is_qr_code(cls, image):
        try:
            qrs = cls.scan(image)
        except Exception:
            return False
        else:
            return True if qrs else False


def test_zbar_scanner():
    from PIL import Image
    import sys
    from StringIO import StringIO
    name = sys.argv[1]
    img = Image.open(name)
    buffer = StringIO()
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    img.save(buffer, "jpeg", quality=95)
    ig = Image.open(buffer)
    print ZbarScanner.is_qr_code(ig)


def get_image_score(image):
    """ 获取图片的分数
    
    :param image: 要打分的图片
    :type image: PIL.Image.Image
    :return: 分数
    :rtype: float
    """
    image = image.convert("L")
    w, h = image.width, image.height
    wt, ht = 200.0, 150.0
    if w < wt or h < ht:
        return 0
    points = w * h
    hist = image.histogram()
    w_h_weight = math.log(((w - wt) / w + (h - ht) / h) / 2 + 1, 2)
    t = min(50, points/10000)
    pixels = [p for p in hist if p > t]
    maxp = max(pixels)
    if len(pixels) == 0:
        return 0
    avg = points / len(pixels)
    gs = [p for p in hist if p >= avg]
    gw = 1.0 * (sum(gs) - maxp) / points
    glen = len(gs) * 1.0
    plen = max([len(pixels), 1])
    g = pow(glen, 2) / (256 * plen)
    alpha = 0.8
    score = pow(gw, 1.0/3) * pow(g, 1.0/2) * alpha + w_h_weight*(1-alpha)
    return score


def get_crop_box(width, height):
    """ 获取裁剪的框 """
    p1, p2 = None, None
    w, h = get_feed_size(width, height)
    if p1 and p2:
        x = (p1[0] + p2[0]) / 2
        y = (p1[1] + p2[1]) / 2
        bw = w / 2
        bh = h / 2
        left = x - bw
        right = x + bw
        upper = y - bh
        lower = y + bh
        if left < 0:
            right -= left
            left = 0
        elif right > width:
            left -= right - width
            right = width
        if upper < 0:
            lower -= upper
            upper = 0
        elif lower > height:
            upper -= lower - height
            lower = height
    else:
        left = (width - w) / 2
        upper = 0
        right = left + w
        lower = upper + h
    return left, upper, right, lower


def crop_and_upload_image(image):
    """  裁剪 feed 图并上传
    
    :param image: 要处理的图片
    :type image: PIL.Image.Image
    :return: 裁剪后的大小,上传后的地址 width, height, oss_url
    :rtype: int, int, str
    """
    w, h = image.width, image.height
    left, upper, right, lower = get_crop_box(w, h)
    box = (left, upper, right, lower)
    crop = image.crop(box)
    if crop.mode != "RGB":
        crop = crop.convert("RGB")
    buffer = StringIO()
    crop.save(buffer, "jpeg", lossless=True)
    data = buffer.getvalue()
    buffer.close()
    headers = {"content-type": "image/jpeg"}
    url = OnlineImageUploader.upload(data=data, suffix="jpg", headers=headers)
    return w, h, url


def choose_feed_images(urls, refer=None, flag=True):
    """  选择适合的图片做 feed 图 
    
    :param urls: 要处理的图片链接
    :type urls: list of str
    :param refer: referer
    :type refer: str or None
    :param flag: 是否使用打分机制选取缩略图
    :type flag: bool
    :return: 返回 feed 图的信息, 包括地址尺寸 width, height, oss_url
    :rtype: dict(FeedImageMeta)
    """

    def get_body_score(body):
        """ 通过 response body 获取图片和分数"""
        image, score = None, 0
        try:
            image = Image.open(StringIO(body))
        except Exception as e:
            logging.error(e.message)
        else:
            score = get_image_score(image)
        return image, score

    responses = http.multidownload(urls=urls, refer=refer)
    result = [get_body_score(r.body) for r in responses if not r.error]
    sorted_result = sorted(result, key=lambda item: item[1], reverse=True)
    scores = set()
    images = list()
    THRESHOLD = 0.2 if flag else 0
    for img, score in sorted_result:
        if score < THRESHOLD or score in scores:
            break
        else:
            scores.add(score)
            images.append(img)
    length = len(images)
    if length == 0:
        return list()
    n = 3 if length >= 3 else 1
    feeds = list()
    for img in images:
        try:
            w, h, url = crop_and_upload_image(img)
        except Exception:
            continue
        else:
            n -= 1
            feed = FeedImageMeta()
            feed.width = w
            feed.height = h
            feed.src = url
            feeds.append(feed.to_dict())
            if n == 0:
                break
    return feeds


def _download_and_upload_images(urls, refer=None, uploader=None):
    if uploader is None:
        uploader = OnlineImageUploader
    responses = http.multidownload(urls=urls, refer=refer)
    for r in responses:
        if r.error:
            raise ImageDownloadError(str(r.error))
    images = [process_image_response(r, uploader) for r in responses]
    return images


def process_image_response(r, uploader=None):
    if uploader is None:
        uploader = OnlineImageUploader
    image = Image.open(StringIO(r.body))
    fingerprint = md5(r.body).hexdigest()
    w, h, qr, gray = get_image_metas(image)
    url = upload_image(r.body, uploader)
    result = ImageMeta()
    result.width = w
    result.height = h
    result.qr = qr
    result.gray = gray
    result.src = url
    result.org = r.effective_url
    result.md5 = fingerprint
    return result.to_dict()


def download_and_upload_images(urls, refer=None, concurrent=5, uploader=None):
    if uploader is None:
        uploader = OnlineImageUploader
    length = len(urls)
    if length < concurrent:
        return _download_and_upload_images(urls, refer, uploader)
    images = list()
    for i in range(0, length, concurrent):
        end = i + concurrent
        images.extend(_download_and_upload_images(urls[i: end], refer, uploader))
    return images
