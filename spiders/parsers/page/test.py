import sys
import requests
from judge_page import JudgePage


if __name__ == '__main__':
    url = sys.argv[1]
    ua = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.133 Safari/537.36"
    r = requests.get(url=url, headers={"user-agent": ua})
    judge = JudgePage()
    result = judge(r.content,url)
    for d in result:
        print d
