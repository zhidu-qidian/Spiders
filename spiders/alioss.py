# coding: utf-8

from hashlib import sha256
from StringIO import StringIO
from types import FileType

import oss2

from settings import OSS_BDP_IMAGES_DOMAIN
from settings import OSS_BDP_IMAGES_ENDPOINT
from settings import OSS_BDP_IMAGES_NAME
from settings import OSS_TEST_DOMAIN
from settings import OSS_TEST_ENDPOINT
from settings import OSS_TEST_NAME

__author__ = "Sven Lee"
__copyright__ = "Copyright 2016-2019, ShangHai Lie Ying"
__license__ = "Private"
__email__ = "lee1300394324@gmail.com"
__date__ = "2016-12-05 11:12"


class ObjectUploader(object):

    access_key_id = ""
    access_key_secret = ""

    def __init__(self, endpoint, name, domain=None):
        auth = oss2.Auth(self.access_key_id, self.access_key_secret)
        self.domain = domain if domain else endpoint
        self.bucket = oss2.Bucket(auth=auth, endpoint=endpoint, bucket_name=name)

    def upload(cls, data, name=None, suffix=None, headers=None):
        if name is None:
            if isinstance(data, (FileType, StringIO)):
                data = data.read()
            name = sha256(data).hexdigest()
            if suffix is not None:
                name = "%s.%s" % (name, suffix)
        retry = 3
        for i in range(retry):
            try:
                cls.bucket.put_object(name, data, headers=headers)
            except Exception:
                if i == retry-1:
                    raise
        return "%s/%s" % (cls.domain, name)


OnlineImageUploader = ObjectUploader(
    endpoint=OSS_BDP_IMAGES_ENDPOINT,
    name=OSS_BDP_IMAGES_NAME,
    domain=OSS_BDP_IMAGES_DOMAIN,
)


TestObjectUploader = ObjectUploader(
    endpoint=OSS_TEST_ENDPOINT,
    name=OSS_TEST_NAME,
    domain=OSS_TEST_DOMAIN,
)
