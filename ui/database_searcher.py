#!/usr/bin/python
# -*- coding: utf-8 -*-

#import players
import pprint
import copy
import sys
from PyQt4.QtCore import *
from PyQt4.QtGui import *
#import resources_database_search

#pp = pprint.PrettyPrinter(indent=4)

class Database_SearchEngine(object):

    def __init__(self, parent=None):
        pass



    def search_for_Phrase(self, service, searchphrase):
        """
        If searchstring as spaces where the filename hasnt, it will return no result
        If a searchstring containing spaces, and no searchresults are found, we will
        replace the space with "_"
        :param searchphrase: Searchstring as QString or String
        :return: dict like this:
        {   'albums': [{   'Lana Del Rey': 'Born to Die'}],
            'artists': ['Lana Del Rey'],
            'files': [],
            'titles': [   {   'album': 'Born to Die',
                              'artist': 'Lana Del Rey',
                              'artistsort': 'Del Rey, Lana',
                              'date': '2012',
                              'file': 'toplevel/LanaDelRay/Born to Die/1 - Born to Die.mp3',
                              'last-modified': '2012-03-24T13:56:04Z',
                              'time': '286',
                              'title': 'Born to Die',
                              'track': '1/12'},
                          {   'album': 'Born to Die',
                              'artist': 'Lana Del Rey',
                              'artistsort': 'Del Rey, Lana',
                              'date': '2012',
                              'file': 'toplevel/LanaDelRay/Born to Die/2 - Off to the Races.mp3',
                              'last-modified': '2012-03-24T13:56:36Z',
                              'time': '300',
                              'title': 'Off to the Races',
                              'track': '2/12'}, ....
        """

        self._service = service
        if self._service is None:
            return {}

        tag ={ 0 : "artist",
               1 : "album",
               2 : "title",
               3 : "filename" }

        #print("search for:", searchphrase)
        result_artist = self._service.search(tag[0], searchphrase)
        #print("result1")
        result_album = self._service.search(tag[1], searchphrase)
        #print("result2")
        result_title = self._service.search(tag[2], searchphrase)
        #print("result3")
        result_filename = self._service.search(tag[3], searchphrase)
        #print("result4")

        overall_searchresult = {}
        ############### Combine Searchresults to a overall dict
        if len(result_artist) > 0:
            overall_searchresult.update({"result_artist" : result_artist})
        else:
            overall_searchresult.update({"result_artist" : []})
        ########################################################             ARTIST
        if len(result_album) > 0:
            overall_searchresult.update({"result_album" : result_album})
        else:
            overall_searchresult.update({"result_album" : []})
        ########################################################             ALBUM
        if len(result_title) > 0:
            overall_searchresult.update({"result_title" : result_title})
        else:
            overall_searchresult.update({"result_title" : []})
        ########################################################             TITLE
        if len(result_filename) > 0:
            overall_searchresult.update({"result_filename" : result_filename})
        else:
            overall_searchresult.update({"result_filename" : []})
        ########################################################              FILENAME
        #print("OVERALL RESULT:",overall_searchresult)
        return self._construct_hirarchy_dict(self._clean_duplicates_return_cleaned_list(overall_searchresult))

    def _clean_duplicates_return_cleaned_list(self, originalDict):

        deltaList = []
        cleaned_result = []
        # collect all filenames which are found by previouse searchmethodes (artist, album, titel. ...)
        for key in originalDict.iterkeys():  #"result_artist","result_album","result_title","result_filename" == []
            for list_item in originalDict[key]: # list_item is a dict {'album': 'Born to Die', 'artist': 'Lana De....'}
                filename_already_detected = list_item["file"]
                if filename_already_detected not in deltaList:
                    cleaned_result.append(list_item)
                    deltaList.append(filename_already_detected)
        #print("Return cleaned results.")
        return cleaned_result # list containing all found dicts but without duplicates

    def _construct_hirarchy_dict(self, list_with_songsDicts):
        """

        :param list_with_songsDicts:
        [{'album': 'Born to Die', 'artist': 'Lana Del Rey', 'track': '10/12', 'title': 'Million Dollar Man',
        'last-modified': '2012-03-24T13:59:14Z', 'artistsort': 'Del Rey, Lana',
        'file': 'toplevel/LanaDelRay/Born to Die/10 - Million Dollar Man.mp3', 'time': '232', 'date': '2012'},
        {'album': 'Born to Die', 'artist': 'Lana Del Rey', 'track': '11/12', 'title': 'Summertime Sadness',
        'last-modified': '2012-03-24T13:59:34Z', 'artistsort': 'Del Rey, Lana',
        'file': 'toplevel/LanaDelRay/Born to Die/11 - Summertime Sadness.mp3', 'time': '265', 'date': '2012'},
        {'album': 'Born to Die', 'artist': 'Lana Del Rey', 'track': '12/12', 'title': 'This Is What Makes Us Girls',
        'last-modified': '2012-03-24T13:59:50Z', 'artistsort': 'Del Rey, Lana',
        'file': 'toplevel/LanaDelRay/Born to Die/12 - This Is What Makes Us Girls.mp3', 'time': '240', 'date': '2012'}]

        :return:
        { 'artists' : ["Lana Del Rey", "Unknown"],
          'albums'  : [{'Lana Del Rey': 'Born to Die'}],
          'titles'  : [{'album': 'Born to Die', 'artist': 'Lana Del Rey', 'track':'10/12', 'title':'Million Dollar Man',
                        'last-modified': '2012-03-24T13:59:14Z', 'artistsort': 'Del Rey, Lana',
                         'file': 'toplevel/LanaDelRay/Born to Die/10 - Million Dollar Man.mp3',
                         'time': '232', 'date': '2012'}, {.....}, {......}] #title is not empty or not existing
          'files'   : [{'last-modified': '2014-06-26T19:41:29Z',
                        'file': 'toplevel/black_hole_sun_Soundgarden.mp3',
                        'time': '346'}]                                     #can not be sorted to any artist or album
        """
        hirarchy_dict = {}
        # ARTISTS: create a list of all available artists:
        artistList = []
        for song in list_with_songsDicts:
            if song.has_key("artist"):
                if song["artist"] != "" and song["artist"] not in artistList:
                    artistList.append(song["artist"])

        # ALBUMS: create a list of all available albums:
        albumsList = []
        ignorelist = []
        for song in list_with_songsDicts:
            if song.has_key("album"):
                if song["album"] != "" and song["album"] not in ignorelist:
                    if song.has_key("artist"):
                        albumsList.append({song["artist"]: song["album"]})
                        ignorelist.append(song["album"])
                    else:
                        albumsList.append({"unknown": song["album"]})
                        ignorelist.append(song["album"])

        ################ Sort entrys of list_with_songDicts in titleList or in fileList
        # TITLES: create a list of song-dictionarys where the "title" entry is existing and not empty
        titlesList = []
        remaining_files = copy.deepcopy(list_with_songsDicts)
        for i in xrange(len(list_with_songsDicts)):
            if list_with_songsDicts[i].has_key("title"):
                #print("Has Title:", list_with_songsDicts[i]["file"])
                if list_with_songsDicts[i]["title"] != "":# and song["title"] not in titlesList:
                    #print("title is not empty")
                    if list_with_songsDicts[i]["title"] not in titlesList:
                        #print("title is not in List.")
                        titlesList.append(list_with_songsDicts[i])
                        #print("Append Song", list_with_songsDicts[i]["title"])
                        print(i)
                        remaining_files.remove(list_with_songsDicts[i])

        # FILES: create a list of all remaining song-dicts
        filesList = []
        for song in remaining_files:
            filesList.append(song)

        hirarchy_dict.update({"artists" : artistList})
        hirarchy_dict.update({"albums" : albumsList})
        hirarchy_dict.update({"titles" : titlesList})
        hirarchy_dict.update({"files" : filesList})
        #print("return hirarchy dict")
        return hirarchy_dict


class LM_QTreeWidget(QTreeWidget):

    def __init__(self, parent=None):
        QTreeWidget.__init__(self, parent)
        self.service = None
        self.setSelectionMode(QAbstractItemView.MultiSelection)
        self.clicked.connect(self.checkSelection_clicked)
        self.expanded.connect(self.checkSelection_expanded)
        self.collapsed.connect(self.checkSelection_collapsed)

        #self.setSortingEnabled(True)
        #self.sortByColumn(0, Qt.AscendingOrder)

    def populateTree(self, searchphrase):

        self.clear()
        self.childFromArtist = {}
        self.parentFromAlbum = {}
        self.childFromAlbum = {}
        self.parentFromTitle = {}

        self.setColumnCount(1)
        self.setHeaderLabels(["Artist/Album/Title"])
        self.setItemsExpandable(True)
        #print("Check Service")
        if self.service is None:
            #print("Service is none")
            return False
        #print("construct searchengine")
        self.searchEngine = Database_SearchEngine()
        #print("Phrase:",searchphrase)
        self.emit(SIGNAL("start_loading"))
        #data = self.searchEngine.search_for_Phrase(searchphrase)

        self.thread = None
        self.thread = WorkerThread(self.searchEngine.search_for_Phrase,self.service, searchphrase.toLocal8Bit())  # Request API using string
        self.thread.start()
        while not self.thread.isFinished():
            QApplication.processEvents()
        data = self.thread.result()
        #print("data received, start populating")
        #print(data)
        #create toplevelitems  (Artist Folders)
        for artist in data['artists']:
            entry0 = QTreeWidgetItem(self, [artist.decode('utf-8')])
            entry0.setIcon(0, QIcon(":/folder.png"))
            self.parentFromAlbum[artist] = entry0

        #create Albums (child folders of Artists)
        for album in data['albums']:
            #print(album.values()[0])
            #print(type(album.values()[0]))
            parentOfAlbum = self.parentFromAlbum[album.keys()[0]]
            entry1 = QTreeWidgetItem(parentOfAlbum, [album.values()[0].decode('utf-8')])
            entry1.setIcon(0, QIcon(":/folder.png"))
            self.parentFromTitle[album.values()[0]] = entry1
            self.childFromArtist[album.keys()[0]] = entry1

        #create titles (childs of Albums)
        for title in data['titles']:
            if title.has_key("album"):
                parentOfTitel = self.parentFromTitle[title["album"]]
            elif title.has_key("artist"):
                parentOfTitel = self.parentFromAlbum[title["artist"]]
            else:
                parentOfTitel = self.parentFromAlbum.get("Unknown Artist")
                if parentOfTitel is None:
                    entry0 = QTreeWidgetItem(self, ["Unknown Artist"])
                    entry0.setIcon(0, QIcon(":/folder.png"))
                    self.parentFromAlbum["Unknown Artist"] = entry0
                    parentOfTitel = entry0

            #print(parentOfTitel)
            entry2 = QTreeWidgetItem(parentOfTitel, [title["title"].decode('utf-8')])
            entry2.setIcon(0, QIcon(":/mp3.png"))
            entry2.setData(0, Qt.UserRole, QVariant((title,)))
            if title.has_key("album"):
                self.childFromAlbum[title["album"]] = entry2
            elif title.has_key("artist"):
                self.childFromArtist[title["artist"]] = entry2
            else:
                self.parentFromAlbum[title["title"]] = entry2

        if len(data["files"]) > 0:
            parentOfTitel = self.parentFromAlbum.get("Unknown Artist")
            if parentOfTitel is None:
                entry0 = QTreeWidgetItem(self, ["Unknown Artist"])
                entry0.setIcon(0, QIcon(":/folder.png"))
                self.parentFromAlbum["Unknown Artist"] = entry0

            for filename in data['files']:
                #print(filename["file"])
                #print(type(filename["file"]))
                parentOfFilename = self.parentFromAlbum["Unknown Artist"]
                entry1 = QTreeWidgetItem(parentOfFilename, [filename["file"].split("/")[-1:][0].decode('utf-8')])
                entry1.setData(0, Qt.UserRole, QVariant((filename,)))
                entry1.setIcon(0, QIcon(":/mp3.png"))
                self.childFromAlbum["Unknown Artist"] = entry1
        self.emit(SIGNAL("stop_loading"))

        print("Population finished.")
        return True

    def markAllChildrenFrom(self, Index):
        #print("idle because isReady is", self.model().isReady)
        childs = self.get_MP3_of_Folder_using_Index(Index)
        for child in childs:
            self.selectionModel().select(child, QItemSelectionModel.Select)

    def get_MP3_of_Folder_using_Index(self, QModelIndex):
        childlist = []
        #print(self.rowCount(QModelIndex))
        for i in xrange(self.model().rowCount(QModelIndex)):
            child = self.model().index(i,0, QModelIndex)
            if child.data(Qt.UserRole).toPyObject() is None:
                continue # ignore children which are folders...
            else:
                childlist.append(child)
        return childlist

    def mark(self, Index):
        self.selectionModel().select(Index, QItemSelectionModel.Select)

    def unmark(self, Index):
        self.selectionModel().select(Index, QItemSelectionModel.Deselect)

    def toggleExpansion(self, Index):
        if self.isExpanded(Index):
            self.collapse(Index)
        else:
            self.expand(Index)
        return True

###########Logic zur Selektion und expand der Dateistruktur ###########################
    def checkSelection_expanded(self, *args):

        initial_selection = self.selectedIndexes()
        childs = self.get_MP3_of_Folder_using_Index(args[0])
        #print("MP3 in Folder:", childs)
        trigger = True
        for child in childs:
            if child not in initial_selection:
                trigger = False
                break

        if trigger:
            # Mark Expanded node
            #print("mark")
            self.mark(args[0])
            # Mark all Childs from Node which are MP3
            #print("mark children")
            self.markAllChildrenFrom(args[0])
        else:
            self.unmark(args[0])

    def checkSelection_clicked(self, *args):

        initial_selection = self.selectedIndexes()

        if args[0] in initial_selection:
            iamselected = True
        else:
            iamselected = False

        if args[0].parent() in initial_selection:
            myparentisselected = True
        else:
            myparentisselected = False

        #if os.path.isdir(self.model().filePath(args[0])):      #do not use os. calls because of network speed.
        if self.model().hasChildren(args[0]):
            #print("Folder")
            iamafolder = True
            iamafile = False
        else:
            #print("File")
            iamafolder = False
            iamafile = True

        #wenn ich ein ordner bin und ich markiert bin, dann werden alle meine childs markiert
        if iamafolder and iamselected:
            #print("Iam a folder an i am selected")
            self.clearSelection()
            self.mark(args[0])
            self.markAllChildrenFrom(args[0])
            #print("expand")
            self.expand(args[0])
        elif iamafolder and not iamselected:
            #print("Iam a folder an i am not selected.")
            childs = self.get_MP3_of_Folder_using_Index(args[0])
            for child in childs:
                self.unmark(child)
        elif iamafile and iamselected:
            #check if all other mp3 from my parent are marked also
            otherchilds = self.get_MP3_of_Folder_using_Index(args[0].parent())
            trigger = True
            for child in otherchilds:
                if child not in initial_selection:
                    trigger = False
            if trigger:
                self.mark(args[0].parent())

        #wenn parentNode markiert ist und args nicht markiert ist, parent nicht mehr markieren
        if myparentisselected and not iamselected:
            parent = args[0].parent()
            #print("Unmark NOW:", parent, self.parentFromAlbum.get(parent))
            #while parent != self:
            self.unmark(parent)
            #    parent = parent.parent()

    def checkSelection_collapsed(self, *args):
        self.clearSelection()

    def get_current_selection(self):

        selection = self.selectedIndexes()
        filepathes = []
        for item in selection:
            if item.data(Qt.UserRole).toPyObject() is None:
                continue # ignore children which are folders...
            else:
                filepathes.append(item.data(Qt.UserRole).toPyObject()[0]['file'].decode('utf-8'))
        return filepathes

    def set_service(self, mpd_service):
        self.service = None
        self.service = mpd_service

class WorkerThread(QThread):
    def __init__(self, function, *args, **kwargs):
        QThread.__init__(self)
        self.function = function
        self.args = args
        self.kwargs = kwargs

    #def __del__(self):
    #    self.wait()

    def run(self):
        #print("Start Process")
        self._result = None
        self._result = self.function(*self.args,**self.kwargs)
        #print("Process finished", self._result)
        return

    def result(self):
        return self._result


if __name__ == "__main__":

    searchphrase = raw_input("Enter Searchstring: ")
    app = QApplication([])
    window = LM_QTreeWidget()

    window.show()
    sys.exit(app.exec_())

#TODO: Erstelle ein Widget (stacked Widget),
#TODO: - Abmaße müssen in das UI passen
#TODO: - Suchfeld einfügen
#TODO: - Anzeige findet im selben Fenster statt indem das Suchfeld ist
#TODO: - Bei klick in das suchgeld, wird eine virtuelle Tastatur angezeigt
#TODO: - Der Suchbefehl wird an die Funktion "Databse_SearchEngine.search_for_Phrase" übergeben
#TODO: - Das Ergebnis wird aufgelöst in ein QTreewidget übergeben und dargestellt
# - Das Treewidget funktioniert wie auch das Treewidget in der Filebrowserdarstellung
#TODO: - flickcharm ist integriert
#TODO: - es gibt einen Button, mit dem man seine aktuelle Auswahl der Playliste hinzufügen kann
#TODO: - sobald eine neue Suche durchgeführt wird, wird das alte Ergebis natürlich verworfen
#TODO: - Es werden Signale emittiert, die ausgewertet werden können, wann der Ladevorgang abgeschlossen ist (splash)
#TODO: - Das widget ist im UI des webradios eingebunden.
#TODO: - Der Butten "zurück" ist umfunktioniert (nur im Mediaplayerbetrieb) und stellt eine Lupe dar
#TODO: - sobald dieser angewählt wird öffnet sich die virtuelle Tastatur
#TODO: - sobald der Suchvorgang gestartet ist erscheint ein "splash" der anzeigt, dass die Suche läuft
#TODO: - sobald die Suche abgeschlossen ist, wechselt die Anzeige zu den Suchergebnissen
# - die Suchergebisse sind aufgebaut wie :
#      +Nirvana
#          +Nevermind
#              Track1
#              Track2
#              Track3
#              .....
#          +Bleech
#              Track1
#              Track2
#              Track3
#              ....
#      +Sonstige
#          +Mixed MP3
#              Track1
#              Track2
#              Track3
#      Track_unknown1
#      Track_unknown2
#      ....
# - Die Tracks die hinzugefügt werden sollen können wie gewohnt ausgewählt werden und mittels eines speziellen
#TODO:   Buttons in die aktuelle Playliste übernommen werden.
#TODO: - Die Ansicht wechselt NICHT automatisch, sondern der User muss auf "home" oder auf den Playlisteditor klicken

