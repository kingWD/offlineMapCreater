#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'gerry'

import httplib
import logging
# import socket.error
import threading
import re

# max bytes read per second.
MAXReadBytes = 10240

# seconds waiting for a response
ResponseTimeout = 30
MAXTryTimes = 5

# url prefix
URLPrefix = 'http://'

DefaultPorts = {
    'HTTP': 80,
    'ftp': 21,
    'HTTPS': 443
}


class DownloadProcessor(threading.Thread):
    '''
    Download processor.
    '''
    pattern = '(?:.*://)([abc](?:\.[a-zA-Z]+)+)(/[a-zA-Z]+/(\d+)/(\d+)/(\d+)\.png)\?base_x=(\d+)&base_y=(\d+)'
    urlPattern = re.compile(pattern)

    def __init__(self, url, queue):
        threading.Thread.__init__(self, name='Download-thread')
        self.url = url
        self.host = None
        self.file = None
        self.contents = ''
        self.try_times = 0
        self.done = False
        self.content_length = 0
        self.queue = queue
        self.x = 0
        self.y = 0
        self.z = 0
        self.base_x = 0
        self.base_y = 0

    def parse_url(self):
        url_match_result = re.findall(DownloadProcessor.urlPattern, self.url)
        if 0 != len(url_match_result):
            self.host = url_match_result[0][0]
            self.file = url_match_result[0][1]
            self.z = int(url_match_result[0][2])
            self.x = int(url_match_result[0][3])
            self.y = int(url_match_result[0][4])
            self.base_x = int(url_match_result[0][5])
            self.base_y = int(url_match_result[0][6])
            return True
        else:
            return False

    def reset(self):
        self.contents = ''
        self.done = False
        self.content_length = 0

    def download(self):
        while (not self.done) and (self.try_times <= MAXTryTimes):
            conn = httplib.HTTPConnection(self.host, timeout=ResponseTimeout)
            try:
                self.try_times += 1
                conn.request('GET', self.file)
                response = conn.getresponse()
                # if the response is not 200 OK or the Content-Length is not bigger than 0
                # it's a bad response ,we need to try again
                if (httplib.OK != response.status) or (response.length <= 0):
                    logging.error('The server sends a wrong response,need to try again')
                    conn.close()
                    self.reset()
                    continue
                # save the Content-Length field in response,this field indicates the total length of the response body.
                self.content_length = response.length
                while response.length > 0:
                    data = response.read(MAXReadBytes)
                    if len(data) <= 0:
                        break
                    self.contents += data
                if len(self.contents) >= self.content_length:
                    self.done = True
                    queue_data = {'x': self.x - self.base_x,
                                 'y': self.y - self.base_y,
                                 'z': self.z,
                                 'contents': self.contents
                                }
                    self.queue.put(queue_data)
                    logging.info("Job done!")

            except Exception as err:
                print err
                logging.error('An error happened!')

            finally:
                conn.close()

    def run(self):
        if self.parse_url():
            self.download()
            if not self.done:
                logging.error('Download failed.x:%(x)s, y:%(y)s, z:%(z)s', {'x':self.x, 'y':self.y, 'z':self.z})
        else:
            logging.error('Wrong url!url:%(url)s', {'url':self.url})