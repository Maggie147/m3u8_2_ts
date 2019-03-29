# -*- coding: utf-8 -*-
"""
@Created On 2019-03-29
@Updated On 2019-03-29
@Author: tx
@Description: Download ts by m3u8 file, Combine many ts to a useful ts_video

"""
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


class TsDownload(object):
    def __init__(self):
        self.session = requests.Session()
        self.session.headers['User-Agent'] = UserAgent().random

    def _check_dir(self, file_dir):
        self.save_path = file_dir
        if not os.path.isdir(file_dir):
            os.makedirs(file_dir)

    def _send_request(self, url):
        i = 0
        while i <= 3:
            try:
                return self.session.get(url=url, stream=True)  # verify=False
            except Exception as e:
                print('[ERROR] %s%s' % (e, url))
                i += 1
        else:
            return None

    def _save_chunk(self, url):
        res = self._send_request(url)
        if not res:
            return 'Failed, url:{}'.format(url)
        file_tmp = os.path.split(url)[-1]
        full_path = os.path.join(self.save_path, file_tmp)
        with open(full_path, "wb+") as fp:
            for chunk in res.iter_content(chunk_size=1024):
                if chunk:
                    fp.write(chunk)
        return full_path

    @func_timer
    def download_use_coroutine(self, urls, save_path):
        """
        使用协程下载
        """
        self._check_dir(save_path)
        spawns = []
        for url in urls:
            spawns.append(gevent.spawn(self._save_chunk, url))

        # 在遇到IO操作时，gevent会自动切换，并发执行（异步IO）
        rets = gevent.joinall(spawns)
        results = [ret.get() for ret in rets]
        return results

    @func_timer
    def download_use_coroutine_pool(self, urls, save_path):
        """
        使用协程池下载
        """
        self._check_dir(save_path)
        pool = Pool(100)
        results = pool.map(self._save_chunk, urls)
        return results


def main():
    base_url = 'https://videos5.jsyunbf.com/2019/02/07/iQX7y3p1dleAhIv7/'
    m3u8_path = './m3u8/playlist.m3u8'
    urls = get_ts_urls(m3u8_path, base_url)

    ts_path = './ts_download'
    ts = TsDownload()
    # res = ts.download_use_coroutine(urls, ts_path)
    res = ts.download_use_coroutine_pool(urls, ts_path)
    from pprint import pprint
    pprint(res)


if __name__ == '__main__':
    main()
