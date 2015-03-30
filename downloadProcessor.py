#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'gerry'

import httplib
import sys
import logging

# max bytes read per second.
MAXReadBytes = 10240

# seconds waiting for a response
ResponseTimeout = 30

# url prefix
URLPrefix = 'http://'

class DownloadProcessor(object):
    '''
    Download processor.
    '''

    def __init__(self, url):
        self.url = url
        self.domain = None
        self.port = None
        self.path = None
        self.file = None

    def ParseURL(self):
        if len(self.url) <= len(URLPrefix):
            logging.error('Wrong url')
            return

        protPos = self.url.lower().find(URLPrefix)
        if -1 == protPos:
            logging.error('Wrong url,pls input a right one!')
            return
        tmpstr = self.url[protPos+len(URLPrefix):]
        hostPos = tmpstr.find('/')
        if -1 == hostPos:
            host = tmpstr
            self.file = '/'

        else:
            host = tmpstr[:hostPos]
            self.file = tmpstr[hostPos:]
        domainPos = host.find(':')
        if -1 == domainPos:
            self.domain = host
            self.port = 80
        else:
            self.domain = host[:domainPos]
            port = host[domainPos+1:]
            try:
                self.port = int(port)
            except ValueError, err:
                logging.error('The port nust be a number between 0 and 65535.We use 80 instead.')
                self.port = 80

