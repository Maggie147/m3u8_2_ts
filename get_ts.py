# -*- coding: utf-8 -*-
"""
@Created On 2019-03-27
@Updated On 2019-03-29
@Author: tx
@Description: Download ts by m3u8 file, Combine many ts to a useful ts_video
M3U8: UTF-8编码格式的M3U文件。
M3U: M3U文件是记录了一个索引纯文本文件。

打开它时播放软件并不是播放它，而是根据它的索引找到对应的音视频文件的网络地址进行在线播放。
原视频数据分割为很多个TS流，每个TS流的地址记录在m3u8文件列表中.
ts 文件一般怎么处理
    只有m3u8文件，需要下载ts文件
    有ts文件，但因为被加密无法播放，需要解码
    ts文件能正常播放，但太多而小，需要合并
提供的ts文件中并没有加密，也就是没有关键字key ，下载ts文件之后直接合并即可
"""
# pip install requests
# pip install fake_useragent
# pip install gevent

import os
import re
import json
import time
import datetime
import requests
from functools import wraps
from functools import partial
from fake_useragent import UserAgent
import gevent
from gevent.pool import Pool
from gevent import monkey
monkey.patch_all()


def func_timer(func):
    """
    装饰器, 计算函数的运行时间
    """
    @wraps(func)
    def function_timer(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        print(func.__name__, end-start)
        return result
    return function_timer


def get_ts_urls(m3u8_path, base_url):
    """
    提取 m3u8 文件里的所有ts的下载路径
    :param m3u8_path: m3u8 文件全路径
    :param base_url:  要拼接的url头
    :return:
    """
    try:
        with open(m3u8_path, "r") as fp:
            lines = fp.readlines()
            for line in lines:
                if line.endswith(".ts\n"):
                    url = base_url + line.strip("\n")
                    yield url
    except Exception as e:
        print("读取m3u8文件失败: %s %s" % e.args, m3u8_path)


class CombineTs(object):
    """
    简单的拼接多个ts成一个完整的ts文件
    """
    @classmethod
    def _file_walker(cls, path):
        file_list = []
        for root, dirs, files in os.walk(path):
            for fn in files:
                p = str(root+'/'+fn)
                file_list.append(p)
        return file_list

    @classmethod
    @func_timer
    def combine(cls, ts_path, combine_path, file_name):
        file_list = cls._file_walker(ts_path)
        file_path = os.path.join(combine_path, file_name)
        if not os.path.isdir(combine_path):
            os.makedirs(combine_path)
        with open(file_path, 'wb+') as fp:
            for i in range(len(file_list)):
                fp.write(open(file_list[i], 'rb').read())
        return file_path


class TsDownload(object):
    """
    根据提供的urls 下载ts, 并保存在指定路径
    """
    session = requests.Session()
    session.headers['User-Agent'] = UserAgent().random

    @classmethod
    def _check_dir(cls, file_dir):
        cls.save_path = file_dir
        if not os.path.isdir(file_dir):
            os.makedirs(file_dir)

    @classmethod
    def _save_chunk(cls, url, my_session):
        try:
            res = my_session.get(url, stream=True)  # verify=False
        except Exception as e:
            print("异常请求: %s %s" % e.args, url)
            try_session = requests.Session()
            try_session.headers['User-Agent'] = UserAgent().random
            res = try_session.get(url, stream=True)
        if not res:
            return 'Failed, url:{}'.format(url)
        file_tmp = os.path.split(url)[-1]
        full_path = os.path.join(cls.save_path, file_tmp)
        with open(full_path, "wb+") as fp:
            for chunk in res.iter_content(chunk_size=1024):
                if chunk:
                    fp.write(chunk)
        return full_path

    @classmethod
    @func_timer
    def download_use_coroutine(cls, urls, save_path):
        """
        使用协程下载
        """
        cls._check_dir(save_path)
        spawns = []
        for url in urls:
            args = {'my_session': cls.session, 'url': url}
            spawns.append(gevent.spawn(cls._save_chunk, **args))

        # 在遇到IO操作时，gevent会自动切换，并发执行（异步IO）
        rets = gevent.joinall(spawns)
        results = [ret.get() for ret in rets]
        return results
        # 32.77349662780762

    @classmethod
    @func_timer
    def download_use_coroutine_pool(cls, urls, save_path):
        """
        使用协程池下载
        """
        cls._check_dir(save_path)
        pool = Pool(100)
        results = pool.map(partial(cls._save_chunk, my_session=cls.session), urls)
        return results
        # 34.0081949


def main():
    base_url = 'https://videos5.jsyunbf.com/2019/02/07/iQX7y3p1dleAhIv7/'
    m3u8_path = './m3u8/playlist.m3u8'
    urls = get_ts_urls(m3u8_path, base_url)

    ts_path = './ts_download'
    TsDownload.download_use_coroutine(urls, ts_path)
    TsDownload.download_use_coroutine_pool(urls, ts_path)
    
    result_file = CombineTs.combine(ts_path, "./ts", "test.ts")
    print("save ts at: ", result_file)


if __name__ == '__main__':
    main()
