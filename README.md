# 资讯爬虫与数据预处理工程(爬虫核心工程)

资讯数据抓取,不同的资讯抓取服务,数据抽取,数据存储

**没有形成爬虫框架,大量业务混合在一起,比较混乱,可考虑拆分各个部分**

## Getting Started

### Prerequisites

python 2.7

参见 requirements.txt 文件

### Service Documentation

主要分为以下三个部分:

- 网页爬虫(包含抓取,解析,存储)
- 特殊爬虫接口服务
- 解析测试接口服务

#### 网页爬虫

```python main.py long``` 运行需要执行时间比较长的任务:

- 资源处理(下载图片等)

```python main.py middle``` 运行需要执行时间一般的任务:

- 列表页解析(可能会下载页面)
- 网页下载
- 视频爬虫
- 段子爬虫

```python main.py short``` 运行需要执行时间较短的任务:

- 任务分配
- 详情页解析
- 数据清洗过滤
- 字段生成(列表页的缩略图)
- 数据存储

```python main.py short```

#### 特殊爬虫接口服务

```python app-service.py weibo``` 微博数据处理

```python app-service.py wechat``` 微信公众号文章数据适配(老版,中间人攻击版本,废弃)

```python app-service.py weixin``` 微信公众号文章数据适配(新版,关注公众号版本)

```python app-service.py app``` 反编译 app 数据存储适配服务

- POST /api/wandoujia 豌豆荚存储适配接口

- POST /api/jike 即刻存储适配接口

- POST /api/weibo 微博存储适配接口

- GET/POST /api/weixin 废弃

- POST /api/click 废弃

- GET /sites 获取爬虫抓取一级源

- GET /channels 获取爬虫抓取二级源

- GET /sitechannels 获取爬虫抓取的一二级源信息

#### 解析测试接口服务

包含列表页解析，翻页解析，详情页解析测试接口

```python test-service.py```

- POST /test/parse/list 列表页解析
- POST /test/parse/page 翻页判断
- POST /test/parse/detail 详情页解析
- POST /test/advertisement 上报广告图片接口

## Authors

* **Sven Lee** - *Senior software engineer* - [lixianyang](https://github.com/lixianyang)

## License

This project is licensed under Genimous Technology Co company
