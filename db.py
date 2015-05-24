#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'gerry'

import sqlite3
from time import sleep
import logging
import threading
import os, shutil
import time

'''
This module is used to save the tiles into a db file.
In this module,we get data from a queue,and save them into a db file.
Structure of the queue data:
    Queue({'x': x,
           'y': y,
           'z': z,
           'contents':contents
           )

we need three tables:
    CREATE TABLE android_metadata (locale TEXT);
    CREATE TABLE tiles (x int, y int, z int, image blob, PRIMARY KEY (x,y,z));
    CREATE INDEX IND on tiles (x,y,z);

'''


class DBAgent(threading.Thread):

    insert_template = 'insert into tiles(x, y, z, image) values(?, ?, ?, ?);'

    def __init__(self, datafile, queue):
        threading.Thread.__init__(self, name='DB-thread')
        self.conn = None
        self.cursor = None
        self.queue = queue
        self.need_stop = False
        self.dbFile = datafile
        '''
        baseDir = os.path.join(os.getcwd(), 'maps')
        mapDir = '{tz.tm_year}{tz.tm_mon}{tz.tm_mday}{tz.tm_hour}{tz.tm_min}'.format(tz=time.localtime())
        mapDir = os.path.join(baseDir, mapDir)
        self.mapFile = os.path.join(mapDir, datafile)
        if os.path.exists(mapDir):
            shutil.rmtree(mapDir)
        os.makedirs(mapDir)
        '''


    def __del__(self):
        pass
        # clear resource
        # self.cursor.close()
        # self.conn.close()

    def create_table(self):
        self.conn = sqlite3.connect(self.dbFile, timeout=5)
        self.cursor = self.conn.cursor()

        ''' create TABLE and INDEX '''
        self.cursor.execute('CREATE TABLE android_metadata (locale TEXT);')
        self.cursor.execute('INSERT into android_metadata(locale) VALUES (\'zh-CN\');')
        self.cursor.execute('CREATE TABLE tiles (x int, y int, z int, image blob, PRIMARY KEY (x,y,z));')
        self.cursor.execute('CREATE INDEX IND on tiles (x,y,z);')

    def insert_image(self):
        while not self.queue.empty():
            data = self.queue.get()
            if self.conn and self.cursor:
                try:
                    self.cursor.execute(DBAgent.insert_template, (data['x'], data['y'], data['z'], sqlite3.Binary(data['contents'])))
                    self.conn.commit()
                except Exception, e:
                    logging.warn('an error happened during insert data!', e)

    def run(self):
        print "DB thread started!"
        self.create_table()
        while True:
            if not self.need_stop:
                self.insert_image()
                sleep(3)
            else:
                if not self.queue.empty():
                    self.insert_image()
                # clear sqlite resources
                self.cursor.close()
                self.conn.close()
                break

    def stop(self):
        self.need_stop = True
