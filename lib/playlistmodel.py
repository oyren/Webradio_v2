#!/usr/bin/env python
# -*- coding: utf-8 -*-
####################################################################################################################
# This lib is providing a model which holds the data of the current playlist provided by mpd
# If the playlist changed, the model will update the data which is shown
####################################################################################################################


from PyQt4.QtCore import *
from PyQt4.QtGui import *
import mpd                  #sudo apt-get install python-mpd python-mpdclient
import sys

def reconnect(func, *default_args, **default_kwargs):
    """
    Reconnects before running
    """

    def wrap(self, *default_args, **default_kwargs):
        try:
            self.client.connect(self.server, self.port)
        except:
            pass

        # sometimes not enough to just connect
        try:
            return func(self, *default_args, **default_kwargs)
        except:
            self.client = mpd.MPDClient()
            self.client.timeout = None
            self.client.idletimeout = None
            self.client.connect(self.server, self.port)

            return func(self, *default_args, **default_kwargs)

    return wrap

class playlistModel(QAbstractListModel):

    def __init__(self, parent = None):
        QAbstractListModel.__init__(self, parent)
        self.server = "localhost"
        self.port = 6600
        # prepare client
        self.client = mpd.MPDClient()
        self.client.timeout = None
        self.client.idletimeout = None
        self.client.connect(self.server, self.port)

        self.__updatePlaylist()
        self.__updateCurrent()

    @reconnect
    def __loadPlaylist(self):
        playlistdata = self.client.playlistid()
        playlist = []
        for entry in playlistdata:
            if "title" in entry:
                if entry["title"] != "":
                    key = "title"
                else:
                    key = "file"
            else:
                key = "file"
            newEntry = playlistEntry(entry[key], entry["id"], entry["pos"])
            playlist.append(newEntry)

        return playlist

    def __updatePlaylist(self):

        self.playlist = self.__loadPlaylist()

    def __updateCurrent(self):
        status = self.client.status()["state"]
        if status == "play":
            if "songid" in self.client.status():
                songID = self.client.status()["songid"]
            else:
                songID = None
        else:
            status = None
            songID = None
        self.status = status
        self.currentSongID = songID

    def rowCount(self, parent=None, *args, **kwargs):
        return len(self.playlist)

    def data(self, index, role=None):

        if role == Qt.DisplayRole:
            return self.playlist[index.row()].name

        if role == Qt.DecorationRole:
            if self.playlist[index.row()].id == self.currentSongID:
                pixmap = QPixmap()
                pixmap.load("/home/matthias/PycharmProjects/Projects/Raspi_WebRadio/res/icons/play.png")

                return QIcon(pixmap)
            else:
                color = QColor("white")
                pixmap = QPixmap(25,25)
                pixmap.fill(color)
                return QIcon(pixmap)

    def updateData(self):
        self.__updatePlaylist()
        self.__updateCurrent()
        index = QModelIndex()
        self.dataChanged.emit(index, index)



class playlistEntry(object):

    def __init__(self, name, id, position):
        self.name = name
        self.id = id
        self.pos = position


if __name__ == "__main__":
    app = QApplication(sys.argv)

    view = QListView()
    model = playlistModel()
    view.setModel(model)

    btn = QPushButton("Update")
    btn.clicked.connect(model.updateData)
    btn.show()

    view.show()
    app.exec_()
