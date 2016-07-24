#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt4.QtGui import QLabel, QFontMetrics, QApplication, QPushButton, QFont, QSizePolicy
from PyQt4.QtCore import *

class Scaling_QLabel(QLabel):
    '''
    A Subclass of QLabel which is self-scaling the font-size that the contents fit into the Size of the QLabel.
    '''
    
    def __init__(self, parent=None):
        super(Scaling_QLabel, self).__init__(parent)
        self.maxFont = None

    def resizeEvent(self, qResizeEvent):
        if not qResizeEvent.oldSize() == QSize(-1, -1) and self.text() != "":
            self.adjustFont()
        return QLabel.resizeEvent(self, qResizeEvent)

    def setText(self, qString):
        if not qString == "":
            QLabel.setText(self, qString)
            self.adjustFont()
            return QLabel.setText(self, qString)
        return QLabel.setText(self, qString)

    def adjustFont(self):
        # --- fetch current parameters ----
        f = self.font()
        cr = self.contentsRect()
        if self.maxFont is not None:
            maximum = self.maxFont.pointSize()
        else:
            maximum = self.font().pointSize()
        # --- find the font size that fits the contentsRect ---
        fs = 1
        while True:
            f.setPointSize(fs)
            br = QFontMetrics(f).boundingRect(self.text())
            if br.height() <= cr.height() and br.width() <= cr.width():
                fs += 1
            else:
                if self.wordWrap() == False:
                    wouldfit = (max(fs - 1, 1))  # if the length have to fit into the label
                    if wouldfit > maximum:
                        wouldfit = maximum
                    f.setPointSize(wouldfit)  # if wordwrap is wanted by the user... he expects wordwrap.
                else:
                    wouldfit = max(fs - 1, 1)*1.5
                    if wouldfit > maximum:
                        wouldfit = maximum
                    f.setPointSize(wouldfit)  # if wordwrap is wanted by the user... he expects wordwrap.
                    #f.setPointSize(max(fs - 1, 1)*1.5)  # if wordwrap is wanted by the user... he expects wordwrap.
                break
        # --- update font size ---
        self.setFont(f)

    def setFont(self, qFont):
        if self.maxFont is None and qFont.pointSize() != -1:  # only remember very first value
            #print("Remember Pointsize", self.text(), qFont.pointSize())
            self.maxFont = qFont
        return QLabel.setFont(self, qFont)

class Scaling_QLabel_pixmap(QLabel):

    def __init__(self, parent=None):
        super(Scaling_QLabel_pixmap, self).__init__(parent)

    def resizeEvent(self, qResizeEvent):
        '''
        During resizes, the Pixmaps need to be reloaded and scaled to keep aspect ratio.
        Remember to disable "scaledContent" otherwise scaled() would have no effect !
        '''
        if self.pixmap() is not None:
            self.setPixmap(self.pixmap().scaled(self.width(), self.height(), Qt.KeepAspectRatio,
                                                  Qt.SmoothTransformation))
        return QLabel.resizeEvent(self, qResizeEvent)

class Scaling_QPushButton_Icon(QPushButton):

    def __init__(self, parent=None):
        super(Scaling_QPushButton_Icon, self).__init__(parent)

    def resizeEvent(self, qResizeEvent):
        self.setIconSize(qResizeEvent.size())
        return QPushButton.resizeEvent(self, qResizeEvent)

class Scaling_QPushButton_Text(QPushButton):
    
    def __init__(self, parent=None):
        super(Scaling_QPushButton_Text, self).__init__(parent)
        self.maxFont = None
        #print("init-QPushbutton")

    def resizeEvent(self, qResizeEvent):
        if not qResizeEvent.oldSize() == QSize(-1, -1) and self.text() != "":
            #print("Adjust because of resize")
            self.adjustFont()
        return QPushButton.resizeEvent(self, qResizeEvent)

    #def setText(self, qString):
    #    if not qString == "":
    #        QPushButton.setText(self, qString)
    #        print("Adjust because of setText", qString)
    #        self.adjustFont()
    #        return QPushButton.setText(self, qString)
    #    return QPushButton.setText(self, qString)

    def adjustFont(self):
        # --- fetch current parameters ----
        f = self.font()
        cr = self.contentsRect()
        if self.maxFont is not None:
            maximum = self.maxFont.pointSize()
        else:
            maximum = 999
        # --- find the font size that fits the contentsRect ---
        fs = 1
        while True:
            f.setPointSize(fs)
            br = QFontMetrics(f).boundingRect(self.text())
            if br.height() <= cr.height() and br.width() <= cr.width():
                fs += 1
            else:
                wouldfit = max(fs - 1, 1)
                if wouldfit > maximum:
                    print wouldfit
                    wouldfit = maximum
                f.setPointSize(wouldfit)  # if wordwrap is wanted by the user... he expects wordwrap.
                #f.setPointSize(max(fs - 1, 1)*1.5)  # if wordwrap is wanted by the user... he expects wordwrap.
                break
        # --- update font size ---
        self.setFont(f)

    def setFont(self, qFont):
        #print("Setfont", qFont.pointSize())
        if self.maxFont is None and qFont.pointSize() != -1:  # only remember very first value
            self.maxFont = qFont
        return QPushButton.setFont(self, qFont)


if __name__ == "__main__":
    app = QApplication([])
    #window = Scaling_QLabel()
    #window.setMinimumSize(QSize(0, 81))
    #font = QFont()
    #font.setPointSize(54)
    #window.setFont(font)
    #window.setTextFormat(Qt.AutoText)
    #window.setScaledContents(False)
    #window.setWordWrap(True)
    #window.setText("This is a Teststring")
    #window.show()

    #window = Scaling_QPushButton_Icon()
    #window.setIcon(QIcon("../res/icons/home.png"))
    #window.setIconSize(window.sizeHint()*2)
    
    window = Scaling_QPushButton_Text()
    sizePolicy = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding)
    sizePolicy.setHorizontalStretch(0)
    sizePolicy.setVerticalStretch(0)
    sizePolicy.setHeightForWidth(window.sizePolicy().hasHeightForWidth())
    window.setSizePolicy(sizePolicy)
    font = QFont()
    font.setPointSize(20)
    window.setFont(font)
    window.setText("Dies ist ein Test mit Point 20")
    
    window.show()
    app.exec_()