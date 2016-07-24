#!/usr/bin/env python

from __future__ import print_function
import os
import time
import sys
import socket
import logging
from PyQt4.QtCore import *
from PyQt4.QtGui import *

cwd = os.path.dirname(os.path.realpath(__file__))      # gives the path, where the script is located
logger = logging.getLogger("webradio")

try:
    import mpd
except ImportError:
    logger.critical("Can't import mpd. Please install the python bindings for MPD (python-mpd or mpd-python)")
    sys.exit(1)

# MPD settings
MPD_HOST = "localhost"
MPD_PORT = 6600
 
# Time to wait in seconds between checking mpd status changes
POLLING_INTERVAL = 1
# Time to wait in seconds between checking for mpd existing
SLEEP_INTERVAL = 5

class MPD_Eventlistener(QObject):

    def __init__(self, parent=None):
        QObject.__init__(self,parent)
        self.trackworker = None

    def startNotifier(self):

        self.trackworker = WorkerThread(self.__run_notifier)
        self.trackworker.start()
        logger.info("Notifier Started")

    def stopNotifier(self):

        if self.trackworker is not None:
            self.trackworker.terminate()                              #terminating a runnig QThread is DANGEROUS ....
            logger.info("Notifier Stopped")
            self.trackworker = None

    def isrunning(self):

        return True if self.trackworker is not None else False

    def __run_notifier(self):
        """Runs the notifier"""
        # Initialise mpd client and wait till we have a connection
        while True:
            logger.info("Startup MPD Listener")
            try:
                client = mpd.MPDClient()
                client.connect(MPD_HOST, int(MPD_PORT))
                logger.info("{0}: Connected to MPD".format(time.strftime("%a, %d %b %Y %H:%M:%S")))
                # Run the observer but watch for mpd crashes
                self.__observe_mpd(client)
            except KeyboardInterrupt:
                logger.warning("\nKeyBoardInterrupt. Thank you for using!")
                sys.exit()
            except (socket.error, mpd.ConnectionError):
                logger.critical("{0}: Cannot connect to MPD".format(time.strftime("%a, %d %b %Y %H:%M:%S")))
                time.sleep(SLEEP_INTERVAL)

    def __observe_mpd(self, client):
        """This is the main function in the script. It observes mpd and notifies the user of any changes."""
        # Loop and detect mpd changes
        last_status = "Initial"
        last_song = "Initial"
        last_station = "Initial"
        last_vol = "Initial"
        last_url = ""
        last_artist = ""
        last_album = ""
        last_playlist = []

        while True:
            # Get status
            current_status = client.status()['state']
            #print(client.status())
            #{'songid': '420', 'playlistlength': '6', 'playlist': '705', 'repeat': '0', 'consume': '0',
            # 'mixrampdb': '0.000000', 'random': '0', 'state': 'play', 'elapsed': '21.557', 'volume': '100',
            # 'single': '0', 'nextsong': '2', 'time': '22:0', 'song': '1', 'audio': '44100:24:2',
            # 'bitrate': '128', 'nextsongid': '421'}

            current_playlist = client.playlistid()

            #print(client.currentsong())
            #{'album': 'Through The Ashes of Empires (Advance)',
            # 'composer': 'Dave McClain/Robert Flynn',
            # 'artist': 'Machine Head',
            # 'track': '1',
            # 'title': 'Imperium',
            # 'pos': '0',
            # 'last-modified': '2006-07-24T18:06:30Z',
            # 'albumartist': 'Machine Head',
            # 'file': '1 imperium.mp3',
            # 'time': '414', 'date': '2003', 'genre': 'Rock', 'id': '140'}


            # There might be errors when getting song details if there is no song in the playlist
            try:
                current_song = client.currentsong()['title']
                #print(client.currentsong())
                #{'id': '431', 'pos': '0', 'name': 'ROCK ANTENNE',
                # 'file': 'http://mp3channels.webradio.antenne.de/rockantenne',
                # 'title': 'ROCK ANTENNE - Rock Nonstop'}

            except KeyError:
                #print("No Station or Song information found !")
                current_song = ""

            try:
                current_artist = client.currentsong()['artist']
            except KeyError:
                current_artist = ""

            try:
                current_album = client.currentsong()['album']
            except KeyError:
                current_album = ""

            try:
                current_url = client.currentsong()['file']

            except KeyError:
                current_url = ""

            if current_status == "stop":
                    current_song = ""

            try:
                current_station = client.currentsong()['name']
            except KeyError:
                current_station = ""

            try:
                current_vol = client.status()['volume']
            except KeyError:
                current_vol = "Initial"

            #print("My Status is:", current_status)
            #print("My Station is:", current_station)
            #print("Playing the song:", current_song)
            if current_status == "play" or current_status == "pause":
                try:
                    timeinfromation = client.status()["time"]
                    timeplayed = timeinfromation.split(":")[0]
                    timetotal = timeinfromation.split(":")[1]

                    #print("TIME:", timeplayed, timetotal)
                    self.emit(SIGNAL("sig_mpd_timeElapsed_information"), timeplayed, timetotal)
                except KeyError:
                    pass



            if current_status != last_status and last_status != "Initial":
                logger.info("((1))Radio Station changed from {0} to {1}".format(last_station, current_station))
                if current_status == "stop" and last_status == "stop":
                    # 4 seconds long, the status was stop.... so it was not only stopped for the next track....
                    self.emit(SIGNAL("sig_mpd_statusChanged"), current_status)
                if current_status == "play":
                    self.emit(SIGNAL("sig_mpd_stationChanged"), current_station, current_url)

            if current_vol != last_vol:
                logger.info("Emit new Volume-Information: {0}".format(current_vol))
                #print("Daemon emitting signal volume changed ...")
                self.emit(SIGNAL("sig_mpd_volumeChanged"), current_vol)


            # If the station has changed, notify the user
            elif current_station != last_station or last_station == "Initial":
                logger.info("((2))Radio Station changed from {0} to {1}".format(last_station, current_station))
                self.emit(SIGNAL("sig_mpd_stationChanged"), current_station, current_url)

            if (current_song != last_song) or \
                            (current_status != last_status and current_status == "play") and last_song != "Initial":
                logger.info("Song change: Station '{0}' changed to '{1}'".format(current_station, current_song))
                self.emit(SIGNAL("sig_mpd_songChanged"), current_song)

            # emit trackinfo, for Track played which is not from a streaming-station. we need different information
            if current_url != last_url and not current_url.startswith("http://") and not current_url == "":
                #print("NOW I will emit a Signal, which carries information about track, interpret and what else...")
                #print("Current_url (corresponding to 'file')", current_url) #03-Deep Inside Myself _ Helpless victim.mp3
                #print("Current_song (corresponds to 'title'", current_song) #Deep Inside Myself / Helpless victim
                #print("Current_artist (corresponds to 'artist'", current_artist) #Deep inside myself
                #print("Current_album (corresponds to 'album'", current_album) #at a late hour
                logger.info("Media_Local_changed: Filename: {0}, Song: {1}, "
                            "Artist: {2}, Album: {3}".format(current_url,current_song,current_artist,current_album))
                self.emit(SIGNAL("sig_mpd_media_local_changed"), current_url,current_song,current_artist,current_album)

            if not current_playlist == last_playlist:
                self.emit(SIGNAL("sig_mpd_playlist_changed"))


            # Save current status to compare with later
            last_status = current_status
            last_song = current_song
            last_station = current_station
            last_vol = current_vol
            last_url = current_url
            last_artist = current_artist
            last_album = current_album
            last_playlist = current_playlist
            # Sleep for some time before checking status again
            time.sleep(POLLING_INTERVAL)


class WorkerThread(QThread):
    def __init__(self, function, *args, **kwargs):
        QThread.__init__(self)
        self.function = function
        self.args = args
        self.kwargs = kwargs

    #def __del__(self):
    #    self.wait()

    def run(self):
        self.function(*self.args,**self.kwargs)
        return


if __name__ == "__main__":

    def onSongChanged(title):
        print("Song Changed to:",title)

    def onStationChanged(station):
        print("Station changed to:",station)

    def onStatusChanged(status):
        print("Status changed to:",status)

    app = QApplication(sys.argv)
    mylistener = MPD_Eventlistener()
    mylistener.connect(mylistener, SIGNAL("sig_mpd_songChanged"), onSongChanged)
    mylistener.connect(mylistener, SIGNAL("sig_mpd_stationChanged"), onStationChanged)
    mylistener.connect(mylistener, SIGNAL("sig_mpd_statusChanged"), onStatusChanged)
    mylistener.startNotifier()
    app.exec_()

