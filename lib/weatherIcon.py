from PyQt4.QtCore import QTimer, Qt
from PyQt4.QtGui import QLabel, QPixmap
import os
#######################################################################################################################
# A WeatherIcon is a QLabel, which is able to take a path where are *.png files are located.
# If in the given path are PNG files, this label will animate a collection of all pngs in the given folder
# So you can store multiple PNGs in a specific folder and name them in a logocal oder [1-100][A-Z]... and in this
# order these pictures will be "animated". If there is only a single one stored in the given folder only this one will
# be shown. The weatherIcon is than in the same behavior than a normal QLable calling its "setPixmap" function.
#######################################################################################################################

# Define a Fallback png File, for the case, that no PNG can be found in the given folder...
FALLBACK = "/home/matthias/PycharmProjects/Projects/Raspi_WebRadio/res/weather/icon/na.png"

class weatherIcon(QLabel):

    def __init__(self, parent=None):
        QLabel.__init__(self, parent)

        self.fileList = []
        self.currentPath = None
        self.totalSteps = 0
        self.currentStep = 0
        self._timer = QTimer(interval=200,
                             timeout=self._animation_step)

    def setPicturePath(self, path):
        """
        If given path containing multiple pictures, these were loaded and shown in an animation,
        if given path containing a single picture, this one will me loaded and shown,
        if given path containing no pictures, a fallback picture will be loaded.

        :param path: "/given/path/to/hopefully/pictures/" (String)
        :return: False if something went wrong, otherwise nothing
        """

        if os.path.exists(path):
            self.currentPath = path
            self.fileList = self.__createFileList(path)
            self._timer.stop()
            self.pixmaps = self.__loadPixmaps(self.fileList)
            if len(self.pixmaps) > 1:
                self._timer.start()
            elif len(self.pixmaps) == 1:
                self.setPixmap(self.pixmaps[0].scaled(self.width(), self.height(), Qt.KeepAspectRatio,
                                                      Qt.SmoothTransformation))
            else: # case len is 0
                self.setPixmap(QPixmap(FALLBACK).scaled(self.width(), self.height(), Qt.KeepAspectRatio,
                                                        Qt.SmoothTransformation))
        else:
            return False

    def __createFileList(self, path):
        """
        Search the given path for *.png Files, list the complete path in a list

        >> ["/path/given/1.png","/path/given/2.png","/path/given/3.png"]

        :param path: path where should be searched (String)
        :return: List, containing all png files with absolute filepath
        """
        files_in_path = os.listdir(path)
        files_in_path.sort()
        pathes = []
        for filename in files_in_path:
            if filename.endswith("png"):
                complete_path = os.path.join(path, filename)
                pathes.append(complete_path)
        return pathes

    def __loadPixmaps(self, Filelist):
        """
        For a given List with absolute Filepathes, create and load every pictue in a Pixmap Oject and save them to a
        list-object, also provide information, how many pixmaps are created and reset current steps that may have
        already changed

        :param Filelist: ["/path/given/1.png","/path/given/2.png","/path/given/3.png"]
        :return: [ PyQt4.PixmapObject,PyQt4.PixmapObject,PyQt4.PixmapObject,]
        """
        pixmaps = []
        for picture in Filelist:
            pic = QPixmap(picture)
            pixmaps.append(pic)
        self.totalSteps = len(pixmaps)
        self.currentStep = 0
        return pixmaps

    def _animation_step(self):
        """
        depending on how many pixmapes are stored in self. pixmaps, this funktion will show every single pixmap
        in alphabethic order in defined interval (see init). If the maximum count (currentStep) is reached, it will
        start once again.
        With this approach it is possible to make simple animations without using a GIF file...
        """
        self.setPixmap(self.pixmaps[self.currentStep].scaled(self.width(), self.height(), Qt.KeepAspectRatio,
                                                             Qt.SmoothTransformation))
        self.update()
        self.currentStep += 1
        if self.currentStep >= self.totalSteps:
            self.currentStep = 0

    def resizeEvent(self, qResizeEvent):
        '''
        During resizes, the Pixmaps need to be reloaded and scaled to keep aspect ratio.
        Remember to disable "scaledContent" otherwise scaled() would have no effect !
        '''
        if self.currentPath is not None:
            self.setPicturePath(self.currentPath)
        return QLabel.resizeEvent(self, qResizeEvent)