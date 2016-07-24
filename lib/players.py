#!/usr/bin/python
# -*- coding: utf-8 -*-


# for MPC_Player            sudo apt-get install mpd mpc  (Linux only)
import mpd                  #sudo apt-get install python-mpd python-mpdclient
import os
import logging
import time

logger = logging.getLogger("webradio")


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



class MPC_Player(object):

    def __init__(self, channel=None):
        """
            Prepare the client and music variables
        """
        # server="localhost", port=6600
        self.server = "localhost"
        self.port = 6600
        logger.info("Start new player")
        # prepare client
        self.client = mpd.MPDClient()
        self.client.timeout = None
        self.client.idletimeout = None
        #print("Connect server and port")
        self.client.connect(self.server, self.port)
        #print("Connected, clearing now")
        self.client.clear()
        if channel is not None:
            self.client.add(channel)
            #print("Add channel ", channel)

        #load own favorites (if does not exist it only produces a failure message on the terminal...)
        self.client.load("favorites")

    @reconnect
    def load_playlist(self, name):
        logger.info("Load Playlist {0}".format(name))
        try:
            self.client.clear()
            self.client.load(name)
            logger.info("Load Playlist {0} OK".format(name))
            return True
        except:
            logger.warning("Load Playlist {0} FAILED".format(name))
            return False

    @reconnect
    def save_playlist(self, name):
        logger.info("Save Playlist {0}".format(name))
        try:
            logger.info("Deleting old Playlist {0}".format(name))
            self.client.rm(name)
        except:
            logger.warning("Deleting old Playlist {0} FAILED".format(name))
            pass
        try:
            self.client.save(name)
            logger.info("Save Playlist {0} OK".format(name))
            return True
        except:
            logger.warning("Save Playlist {0} FAILED".format(name))
            return False


    @reconnect
    def play(self):
        time.sleep(1)
        self.client.play()

    @reconnect
    def clear(self):
        self.client.clear()

    @reconnect
    def pause(self):
        self.client.pause()

    @reconnect
    def stop(self):
        self.client.stop()

    @reconnect
    def next(self):
        self.client.next()

    @reconnect
    def previous(self):
        self.client.previous()

    @reconnect
    def volume(self, level=None, interval=None):

        if level:
            self.client.setvol(int(level))
            return

        if interval:
            level = int(self.client.status()['volume']) + int(interval)
            self.client.setvol(int(level))
            return

    @reconnect
    def add(self, absoluteFilePath, MusicFolder):
        """
        Adds the given path to the current playlist.
        If the path is a single File, only the filename will be added.
        If the path is a directory, all files, and sub-folders (including files) will be added.

        :param absoluteFilePath: "/home/user/Music/myfile.mp3"
        :param MusicFolder: the Music-Folder wich is specified in mpd-conf
        :return: id of the "Track" added or False if something was wrong.
        """

        path = absoluteFilePath

        #if not os.path.exists(path): return False

        if os.path.isfile(path) and path.endswith((".mp3",".MP3")) and path.startswith(MusicFolder):
            print("Provided path is a mp3-file")
            pathToAdd = path.split(MusicFolder)[1][1:]
            song_id = self.client.addid(pathToAdd.encode('utf-8'))
            return song_id
        else:
            return False

    @reconnect
    def addid(self, link_or_path):
        #print("Player adds:", link_or_path)
        return self.client.addid(link_or_path.encode('utf-8'))

    @reconnect
    def get_id_of_title(self, title):
        """
        Give me a title of a song in my playlist, and I will tell you the corresponding id.
        :param title: "My_great_song.mp3"
        :return: ID (402) or False if title was not found in playlist.
        """
        try:
            playlistInclID = self.get_playlistWithId()
        except:
            return False
        for entry in playlistInclID:
            if str(title).endswith(entry["file"]):
                #print("Found File")
                return entry["id"]

        return False

    @reconnect
    def get_current_playing_filename(self):
        try:
            currentID = self.status("songid")
            playlist = self.get_playlistWithId()
            filepath = None
        except:
            return filepath
        for entry in playlist:
            if int(currentID) == int(entry["id"]):
                filepath=entry["file"]
                break
        return filepath


    @reconnect
    def listAll(self):
        return self.client.listall()

    @reconnect
    def get_playlistWithId(self):
        return self.client.playlistid()

    @reconnect
    def play_title_with_ID(self, id):
        return self.client.playid(int(id))

    @reconnect
    def updateDatabase(self, path=""):
        """

        :param path: (optional) path inside Musicfolder
        :return: --
        """
        self.client.update(path)

    @reconnect
    def setRepeat(self, arg):
        """
        :param arg: TRUE or FALSE
        :return: True if operation succeded else False
        """
        try:
            self.client.repeat('1' if arg else '0')
            return True
        except:
            return False

    @reconnect
    def status(self, key):
        #print(client.status())
        #{'songid': '420', 'playlistlength': '6', 'playlist': '705', 'repeat': '0', 'consume': '0',
        # 'mixrampdb': '0.000000', 'random': '0', 'state': 'play', 'elapsed': '21.557', 'volume': '100',
        # 'single': '0', 'nextsong': '2', 'time': '22:0', 'song': '1', 'audio': '44100:24:2',
        # 'bitrate': '128', 'nextsongid': '421'}
        try:
            value = self.client.status()[key]
        except KeyError:
            value = ""
        return value

    @reconnect
    def removeAllPlaylistEntrysStartingWithFilePath(self, path):
        #print("remove all playlist entrys starting with", path)
        playlist = self.get_playlistWithId()
        #print(playlist)
        for entry in playlist:
            filepath=entry["file"]
            #print("path=",filepath)
            ID_to_delete=entry["id"]
            #print("id=", ID_to_delete)
            if str(filepath).startswith(str(path)):
                #print("deleting")
                self.client.deleteid(ID_to_delete)
        #print("finished")
        return True

    @reconnect
    def search(self, tag, searchphrase):
        """
        :param tag: "artist" "album" "title" "filename"
        :param searchphrase: String or QString
        :return: List containing dictionarys for every searchresult

        EXAMPLE: [{'album': 'Born to Die', 'artist': 'Lana Del Rey', 'track': '12/12',
        'title': 'This Is What Makes Us Girls', 'last-modified': '2012-03-24T13:59:50Z',
        'artistsort': 'Del Rey, Lana', 'file': 'toplevel/LanaDelRay/Born to Die/12 - This Is What Makes Us Girls.mp3',
        'time': '240', 'date': '2012'}]

        """
        #print("player searching for", searchphrase, tag)
        return self.client.search(str(tag), searchphrase)




if __name__ == "__main__":

    player = MPC_Player("http://http-live.sr.se/p1-mp3-192")

    while True:
        command = raw_input("command (play,stop,new,exit)\n")
        if command == "play":
            player.play()
        if command == "stop":
            player.stop()
        if command == "new":
            channel = raw_input("new radio channel")
            player.stop()
            player = MPC_Player(channel)
            player.play()
        if command == "exit":
            break
        if command == "status":
            key = raw_input("key: ")
            print(player.status(key))
        if command == "playlist":
            print(player.get_playlistWithId())

