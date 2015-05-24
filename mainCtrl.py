#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'gerry'

import os, shutil
import downloadProcessor
import db
import logging
import math
import Queue
import random
import time
# import pdb

mapStyle = {
    'openCycle': 'cycle',
    'landscape': 'landscape'
}

# max threads during downloading tiles.
MAXDownLoadThreads = 5


class TileTask(object):
    servers = ['a', 'b', 'c']

    def __init__(self, min_lon, max_lon, min_lat, max_lat, levels, name='test'):
        self.queue = Queue.Queue()
        self.threadNum = 0
        self.downloadThreads = []
        self.min_lon = min_lon
        self.min_lat = min_lat
        self.max_lon = max_lon
        self.max_lat = max_lat
        self.levels = levels
        self.xmlFile = None
        self.dbFile = None
        self.mapName = name
        self.createFile(name)

        # create and start db thread.
        self.dbThread = db.DBAgent(self.dbFile, self.queue)
        self.dbThread.start()
        print "start db thread!"

    def dispatch_task(self, url):
        print "Downloading : %s" % url
        download = downloadProcessor.DownloadProcessor(url, self.queue)
        download.start()
        self.downloadThreads.append(download)

    def get_tiles_by_level(self, level):
        logging.debug('Entering TileTask.get_tiles_by_level!level=%(level)d', {'level':level})
        ntlx, ntly = MapAlgo.degree2num(self.min_lon, self.max_lat, level)
        nbrx, nbry = MapAlgo.degree2num(self.max_lon, self.min_lat, level)

        min_lon_deg, max_lat_deg = MapAlgo.num2degree(ntlx, ntly, level)
        max_lon_deg, min_lat_deg = MapAlgo.num2degree(nbrx, nbry, level)
        logging.debug('Insert xml node')
        xmlNode = MapXML(self.mapName, min_lon_deg, min_lat_deg, max_lon_deg, max_lat_deg, level, nbrx - ntlx + 1, nbry - ntly + 1)
        xmlNode.write_level_node(self.xmlFile)

        parameter = '?base_x={0}&base_y={1}'.format(ntlx, ntly)
        try:
            for x in range(ntlx, nbrx+1, 1):
                for y in range(ntly, nbry+1, 1):
                    server = TileTask.servers[random.randrange(len(TileTask.servers))]
                    url = 'http://{0}.tile.thunderforest.com/cycle/{1}/{2}/{3}.png'.format(server, level, x, y)
                    while True:
                        for thread in self.downloadThreads:
                            if not thread.isAlive():
                                self.downloadThreads.remove(thread)
                        if len(self.downloadThreads) < MAXDownLoadThreads:
                            self.dispatch_task(url + parameter)
                            break
                        else:
                            time.sleep(2)
        except KeyboardInterrupt:
            pass
        finally:
            # wait until download thread stop.
            while True:
                for thread in self.downloadThreads:
                    if not thread.isAlive():
                        self.downloadThreads.remove(thread)
                if not self.downloadThreads:
                    break
                else:
                    time.sleep(1)
            # stop db thread
            self.dbThread.stop()
            if self.xmlFile:
                self.xmlFile.close()

    def get_tiles(self):
        logging.debug('Entering TileTask.get_tiles!')
        for level in self.levels:
            logging.info('Now downloading tiles of level %(level)d', {'level':level})
            self.get_tiles_by_level(level)

    def createFile(self, name):
        logging.debug('Entering TileTask.create_xml_file!')
        baseDir = os.path.join(os.getcwd(), 'maps')
        mapDir = '{mapName}{tz.tm_year}{tz.tm_mon}{tz.tm_mday}{tz.tm_hour}{tz.tm_min}'.format(mapName=name, tz=time.localtime())
        mapDir = os.path.join(baseDir, mapDir)
        self.dbFile = os.path.join(mapDir, 'OruxMapsImages.db')
        if os.path.exists(mapDir):
            shutil.rmtree(mapDir)
        os.makedirs(mapDir)

        self.xmlFile = file(os.path.join(mapDir,  name+'.otrk2.xml'), 'wb')


class MapAlgo(object):
    @staticmethod
    def degree2num(lon_deg, lat_deg, level):
        lat_rad = math.radians(lat_deg)
        n = 2.0 ** level
        xtile = int((lon_deg + 180.0) / 360.0 * n)
        ytile = int((1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi) / 2.0 * n)

        return xtile, ytile

    @staticmethod
    def num2degree(xtile, ytile, level):
        n = 2.0 ** level
        lon_deg = xtile / n * 360.0 - 180.0
        lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
        lat_deg = math.degrees(lat_rad)
        return lon_deg, lat_deg


class MapXML(object):
    levelTemplate = r'''<OruxTracker versionCode="2.1">
<MapCalibration layers="false" layerLevel="{self.level}">
<MapName><![CDATA[{self.mapName}]]></MapName>
<MapChunks xMax="{self.xMax}" yMax="self.yMax" datum="WGS84" projection="Mercator" img_height="256" img_width="256" file_name="{self.mapName}" />
<MapDimensions height="{self.mapHeight}" width="{self.mapWidth}" />
<MapBounds minLat="{self.minLat:.15f}" maxLat="{self.maxLat:.15f}" minLon="{self.minLon:.15f}" maxLon="{self.maxLon:.15f}" />
<CalibrationPoints>
<CalibrationPoint corner="TL" lon="{self.minLon:.6f}" lat="{self.maxLat:6f}" />
<CalibrationPoint corner="BR" lon="{self.maxLon:.6f}" lat="{self.minLat:6f}" />
<CalibrationPoint corner="TR" lon="{self.maxLon:.6f}" lat="{self.maxLat:6f}" />
<CalibrationPoint corner="BL" lon="{self.minLon:.6f}" lat="{self.minLat:6f}" />
</CalibrationPoints>
</MapCalibration>
</OruxTracker>
'''
    xmlHeader = r'''<?xml version="1.0" encoding="UTF-8"?>
<OruxTracker xmlns="http://oruxtracker.com/app/res/calibration"
 versionCode="3.0">
<MapCalibration layers="true" layerLevel="0">
<MapName><![CDATA[{self.mapName}]]></MapName>
'''
    xmlFooter = r'''</MapCalibration>
</OruxTracker>
'''

    def __init__(self, name, min_lon=0.0, min_lat=0.0, max_lon=0.0, max_lat=0.0, level=0, x_max=0, y_max=0):
        self.minLon = min_lon
        self.maxLon = max_lon
        self.minLat = min_lat
        self.maxLat = max_lat
        self.level = level
        self.xMax = x_max
        self.yMax = y_max
        self.mapHeight = y_max * 256
        self.mapWidth = x_max * 256
        self.mapName = name

    def write_header(self, fp):
        fp.write(MapXML.xmlHeader.format(self=self))

    def write_footer(self, fp):
        fp.write(MapXML.xmlFooter)

    def write_level_node(self, fp):
        fp.write(MapXML.levelTemplate.format(self=self))


def main():
    tileTask = TileTask(118.758068, 118.987690, 32.014305, 32.112647, [15])
    tileTask.get_tiles()

if __name__ == '__main__':
    main()
