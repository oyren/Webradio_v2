#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from PyQt4.QtCore import *
from PyQt4.QtGui import *



class LM_QFileSystemModel(QFileSystemModel):

    directoryLoading = pyqtSignal()
    def __init__(self, parent=None):
        QFileSystemModel.__init__(self, parent)
        self.setNameFilterDisables(False)
        self.isReady = True
        self.directoryLoading.connect(self.__busy)
        self.directoryLoaded.connect(self.__ready)

    def __busy(self, arg=None):
        self.isReady = False

    def __ready(self, arg=None):
        self.isReady = True

    def isReady(self):
        return self.isReady

    def fetchMore(self, QModelIndex):
        #self.emit(SIGNAL("loading"))
        self.directoryLoading.emit()
        return QFileSystemModel.fetchMore(self, QModelIndex)

    def get_MP3_of_Folder_using_Index(self, QModelIndex):
        childlist = []
        #print(self.rowCount(QModelIndex))
        for i in xrange(self.rowCount(QModelIndex)):
            child = self.index(i,0, QModelIndex)
            if self.filePath(child).endsWith('.mp3') or self.filePath(child).endsWith('.MP3'):
                childlist.append(child)
        return childlist

    def get_childs(self, QModelIndex):
        childlist = []
        for i in xrange(self.rowCount(QModelIndex)):
            child = self.index(i,0, QModelIndex)
            childlist.append(child)
        return childlist


class LM_QTreeView(QTreeView):

    def __init__(self, parent=None):
        QTreeView.__init__(self, parent)
        self.clicked.connect(self.checkSelection_clicked)
        self.expanded.connect(self.checkSelection_expanded)
        self.collapsed.connect(self.checkSelection_collapsed)

    def markAllChildrenFrom(self, Index):
        QApplication.processEvents()
        #print("idle because isReady is", self.model().isReady)
        while self.model().isReady == False: #idle until model is ready creating all childs.
            #print("idle because isReady is", self.model().isReady)
            QApplication.processEvents()

        childs = self.model().get_MP3_of_Folder_using_Index(Index)
        for child in childs:
            self.selectionModel().select(child, QItemSelectionModel.Select)

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
        childs = self.model().get_MP3_of_Folder_using_Index(args[0])
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
        #print(self.model.filePath(args[0].parent()))
        #print(self.model.filePath(self.view.rootIndex()))

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
            childs = self.model().get_MP3_of_Folder_using_Index(args[0])
            for child in childs:
                self.unmark(child)
        elif iamafile and iamselected:
            #check if all other mp3 from my parent are marked also
            otherchilds = self.model().get_MP3_of_Folder_using_Index(args[0].parent())
            trigger = True
            for child in otherchilds:
                if child not in initial_selection:
                    trigger = False
            if trigger:
                self.mark(args[0].parent())

        #wenn parentNode markiert ist und args nicht markiert ist, parent nicht mehr markieren
        if myparentisselected and not iamselected:
            parent = args[0].parent()
            while self.model().filePath(parent) != self.model().filePath(self.rootIndex()):
                self.unmark(parent)
                parent = parent.parent()

    def checkSelection_collapsed(self, *args):
        self.clearSelection()


class Simulator_Mainwindow(QMainWindow):

    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent)
        self.view = LM_QTreeView(self)
        self.model = LM_QFileSystemModel()
        self.model.setRootPath("/home/matthias/Musik")
        self.model.setFilter(QDir.NoDotAndDotDot|QDir.AllEntries|QDir.AllDirs)
        self.model.setNameFilters(['*.mp3', '*.MP3'])

        self.view.setModel(self.model)
        self.view.setRootIndex(self.model.index("/home/matthias/Musik"))
        self.view.setSelectionMode(QAbstractItemView.MultiSelection)
        self.view.setAnimated(False)
        self.setCentralWidget(self.view)

        for i in range(1,4):
            self.view.hideColumn(i)



if __name__ == "__main__":

    app = QApplication(sys.argv)
    Foldericon = QIcon("folder.png")
    mainwindow = Simulator_Mainwindow()

    mainwindow.show()

    sys.exit(app.exec_())