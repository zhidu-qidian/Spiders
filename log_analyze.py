# coding:utf-8

"""分析日志，汇报解析异常"""

DEBUG = True

import re
import datetime
from urllib import quote
from pymongo import MongoClient
from bson import ObjectId

# 数据库相关
NEW_USER = "third"
NEW_PASSWORD = quote("@Mongo!%&Server@")
if DEBUG:
    NEW_HOST_PORT = "120.27.162.246"
else:
    NEW_HOST_PORT = "10.47.54.77:27017"
NEW_DATABASE = "thirdparty"
NEW_MONGO_URL = "mongodb://{0}:{1}@{2}/{3}".format(NEW_USER,
                                                   NEW_PASSWORD,
                                                   NEW_HOST_PORT,
                                                   NEW_DATABASE)
MONGO_URL = NEW_MONGO_URL
Client = MongoClient(host=MONGO_URL)
DB_M = Client.get_default_database()


class Analyzer(object):
    def grep_general_error(self, text):
        p = re.compile(
            '(?P<time>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})(?P<task>.*?)ERROR(?P<error_info>.*?)\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}',
            re.S)
        grep_result = p.findall(text)
        grep_result = filter(lambda x: x, grep_result)
        grep_result.sort(key=lambda x: x[2])
        result = []
        for num, i in enumerate(grep_result):
            if num > 0:
                if i[2] != grep_result[num - 1][2]:
                    result.append(i)
            else:
                result.append(i)
        grep_result = result
        return grep_result

    def grep_list_error(self, text):
        list_error_p = re.compile("List parse error channel: (.*?) config:")
        cid = list_error_p.findall(text)
        if cid:
            return cid[0].strip()
        else:
            return None

    def grep_detail_error(self, text):
        detail_error_p = re.compile("Detail parse error.*?: (.{24})")
        request_id = detail_error_p.findall(text)
        if request_id:
            request_id = request_id[0].strip()
            request_info = DB_M.v1_request.find_one({"_id": ObjectId(request_id)}, {"channel": 1})
            cid = request_info["channel"]
            return cid
        else:
            return None

    def gen_result(self, cid):
        try:
            c_info = DB_M.spider_channels.find_one({"_id": ObjectId(cid)})
            site = DB_M.spider_sites.find_one({"_id": ObjectId(c_info["site"])})
            site_name = site["name"]
            site_domain = site["domain"]
            channel_name = c_info["name"]
            one_info = dict(
                site_name=site_name,
                site_domain=site_domain,
                channel_name=channel_name,
                cid=cid)
        except:
            one_info = dict()
        return one_info

    def run(self, date=None):
        if not date:
            date = datetime.datetime.now() - datetime.timedelta(days=1)
            date = "." + date.strftime("%Y-%m-%d")
        else:
            date = ""
        logfile = "log-server.log" + date
        log_handler = open(logfile)
        log_content = log_handler.read()
        log_handler.close()
        general_result = self.grep_general_error(log_content)
        report_result = []
        print len(general_result)
        for item in general_result:
            task = item[1]
            error_info = item[2]
            one_item = {
                "date": date.strip("."),
                "type": "unknown-error",
                "task": task,
                "error_info": error_info,
                "ex_info": ""
            }
            list_cid = self.grep_list_error(error_info)
            if list_cid:
                print "list"
                ex_info = self.gen_result(list_cid)
                one_item["ex_info"] = ex_info
                one_item["type"] = "list-error"
                report_result.append(one_item)
            else:
                detail_cid = self.grep_detail_error(error_info)
                if detail_cid:
                    print "detail"
                    ex_info = self.gen_result(detail_cid)
                    one_item["ex_info"] = ex_info
                    one_item["type"] = "detail-error"
                    report_result.append(one_item)
                else:
                    print "unknown"
            DB_M.exception_report.insert(one_item)
            report_result.append(one_item)
        return report_result


if __name__ == "__main__":
    a = Analyzer()
    a.run()
