# -*- coding: utf-8 -*-
"""
@Created On 2019-03-29
@Updated On 2019-03-29
@Author: tx
@Description: Download ts by m3u8 file, Combine many ts to a useful ts_video

使用多线程方式  做对比(不推荐使用)
电脑非常卡, 不好用
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
from threading import Thread
from queue import Queue
from multiprocessing.dummy import Pool


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


class TsDownload(Thread):
    def __init__(self, url, que, save_path):
        super(TsDownload, self).__init__()
        self.url = url
        self.que = que
        self.headers = {
            'User-Agent': UserAgent().random 
        }
        self._check_dir(save_path)

    def _check_dir(self, file_dir):
        self.save_path = file_dir
        if not os.path.isdir(file_dir):
            os.makedirs(file_dir)
  
    def _send_request(self, url):
        i = 0
        while i <= 3:
            try:
                return requests.get(url=url, headers=self.headers, stream=True)  # verify=False
            except Exception as e:
                print('[ERROR] %s%s'% (e, url))
                i += 1
        else:
            self.que.put('failed url: {}'.format(url))
            return None

    def _save_chunk(self):
        url = self.url
        res = self._send_request(url)
        if not res:
            return
        file_tmp = os.path.split(url)[-1]
        full_path = os.path.join(self.save_path, file_tmp)
        with open(full_path, "wb+") as fp:
            for chunk in res.iter_content(chunk_size=1024):
                if chunk:
                    fp.write(chunk)
        # self.que.put('save_path: {}'.format(full_path))

    def run(self):
        self._save_chunk()


@func_timer
def download_use_thread(url_list, save_path):
    """
    使用多进程实现
    """
    q = Queue()
    thread_list = []
    for url in url_list:
        p = TsDownload(url, q, save_path)   
        p.start() 
        thread_list.append(p)

    for i in thread_list:
        i.join()

    # while not q.empty():
    #     # print(q.get())
    #     pass


def main():
    base_url = 'https://videos5.jsyunbf.com/2019/02/07/iQX7y3p1dleAhIv7/'
    m3u8_path = './m3u8/playlist.m3u8'
    urls = get_ts_urls(m3u8_path, base_url)

    ts_path = './ts_download'
    download_use_thread(urls, ts_path)


if __name__ == '__main__':
    main()
