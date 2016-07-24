#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtDeclarative import *
import os
try:
    from lib import global_vars
except ImportError:
    global_vars = QObject()
    global_vars.configuration = {"GENERAL": {"sleeptimerdigitalspinbox":False}}  #use spinner
    #global_vars.configuration = {"GENERAL": {"sleeptimerdigitalspinbox":True}}  #use spinbox

cwd = os.path.dirname(os.path.realpath(__file__))      # gives the path, where the script is located


class SleepTimer(QWidget):
    '''
    A resizable Widget with two Spinboxes Labeled with "h" and "min", also a Time-bomb containing a countdownclock.
    If a spinbox is changed, start is triggered. After 2 Seconds, countdown is startet.
    When countdown ends, signal "sleepTimerelapsed()" is emitted.
    '''
    sleepTimerelapsed = pyqtSignal()
    sleepTimertenseconds = pyqtSignal()

    def __init__(self, parent=None):
        super(SleepTimer, self).__init__(parent)
        self.forceSpinBoxWidget = global_vars.configuration.get("GENERAL").get("sleeptimerdigitalspinbox")
        self.setStyleSheet("SleepTimer {"
                            "background-color: rgb(76, 76, 76);"
                            "color: rgb(240, 240, 240);"
                            "}"
                           "QLabel {"
                           "color: white;"
                           "}"
                           "QSpinBox {"
                           "padding-right: 10px; /* make room for the arrows */"
                           "border-width: 3;"
                           "}"
                           "QSpinBox::up-button {"
                           "width: 26px;"
                            "}"
                           "QSpinBox::down-button {"
                           "width: 26px;"
                            "}"
                            )
        self.value = 0 # the value is calculated in self.active (calculated seconds in total)
        self.isActive = False

        if self.forceSpinBoxWidget:
            self.sb_hours = LeadingZeroSpinBox()
            self.sb_hours.setRange(0,23)
            self.sb_hours.setAlignment(Qt.AlignCenter)
            self.sb_hours.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        else:
            self.sb_hours = QDeclarativeView()
            self.sb_hours.setSource(QUrl(os.path.join(cwd,'sb_hours.qml')))
            self.sb_hours.setResizeMode(QDeclarativeView.SizeViewToRootObject)
            self.sb_hours.setStyleSheet("background:transparent;")
            self.sb_hours.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

            self.sb_hours_obj = self.sb_hours.rootObject().findChild(QObject, "spinner")
            self.sb_hours_value = QDeclarativeProperty(self.sb_hours.rootObject().findChild(QDeclarativeItem, name="spinner"),"currentIndex")

        if self.forceSpinBoxWidget:
            self.sb_minutes = LeadingZeroSpinBox()
            self.sb_minutes.setRange(0,59)
            self.sb_minutes.setAlignment(Qt.AlignCenter)
            self.sb_minutes.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        else:
            self.sb_minutes = QDeclarativeView()
            self.sb_minutes.setSource(QUrl(os.path.join(cwd,'sb_minutes.qml')))
            self.sb_minutes.setResizeMode(QDeclarativeView.SizeViewToRootObject)
            self.sb_minutes.setStyleSheet("background:transparent;")
            self.sb_minutes.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

            self.sb_minutes_obj = self.sb_minutes.rootObject().findChild(QObject, "spinner")
            self.sb_minutes_value = QDeclarativeProperty(self.sb_minutes.rootObject().findChild(QDeclarativeItem, name="spinner"),"currentIndex")



        tmpFont = QFont()
        tmpFont.setPointSize(18)
        self.lbl_hours = QLabel(QString("h"))
        self.lbl_hours.setFont(tmpFont)
        self.lbl_minutes = QLabel(QString("min"))
        self.lbl_minutes.setFont(tmpFont)

        # Load QML Widget Bomb
        self.bomb = QDeclarativeView()
        self.bomb.setSource(QUrl(os.path.join(cwd,'timebomb.qml')))
        self.bomb.setResizeMode(QDeclarativeView.SizeViewToRootObject)
        #self.bomb.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.bomb.setStyleSheet("background:transparent;")
        self.bomb_text = QDeclarativeProperty(self.bomb.rootObject().findChild(QDeclarativeItem, name="counter_text"),"text")

        #setup layouts
        tmpLayout = QHBoxLayout()
        tmpLayout.addSpacerItem(QSpacerItem(40, 40, QSizePolicy.Expanding))
        tmpLayout.addWidget(self.sb_hours)
        tmpLayout.addWidget(self.lbl_hours)
        tmpLayout.addWidget(self.sb_minutes)
        tmpLayout.addWidget(self.lbl_minutes)
        tmpLayout.addSpacerItem(QSpacerItem(40, 40, QSizePolicy.Expanding))

        tmp2Layout = QVBoxLayout()
        tmp2Layout.addLayout(tmpLayout)
        tmp2Layout.addWidget(self.bomb)
        tmp2Layout.addSpacerItem(QSpacerItem(40, 40, QSizePolicy.Expanding))

        self.setLayout(tmp2Layout)
        self.blockValueSignal = False  # if this is true, valueChanged signal is not evaluated
        if self.forceSpinBoxWidget:
            self.sb_hours.valueChanged.connect(self.onValueChanged)
            self.sb_minutes.valueChanged.connect(self.onValueChanged)
        else:
            self.sb_hours_obj.currentIndexChanged.connect(self.onValueChanged)
            self.sb_minutes_obj.currentIndexChanged.connect(self.onValueChanged)


        # setup Timer which is started as soon as a value is changed in any of the spinboxes
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.setInterval(2000)  # 2 seconds until timer starts automatically
        self.connect(self.timer, SIGNAL("timeout()"), self.activate)

        #setup Timer which is a second-timer. It is startet with the self.timer (see self.active)
        self.countDown = QTimer()
        self.countDown.setInterval(1000) #sec
        self.connect(self.countDown, SIGNAL("timeout()"), self.check)

    def onValueChanged(self):

        if self.forceSpinBoxWidget:
            value_sb_hours = self.sb_hours.value()
            value_sb_minutes = self.sb_minutes.value()
        else:
            value_sb_hours = self.sb_hours_value.read().toInt()[0]
            value_sb_minutes = self.sb_minutes_value.read().toInt()[0]

        if self.blockValueSignal:
            return

        if value_sb_hours == 0 and value_sb_minutes == 0:
            print("Stop Timer")
            self.bomb_text.write("Abbruch")
            self.timer.stop()
            self.countDown.stop()
            self.isActive = False
            return

        if self.countDown.isActive():
            self.countDown.stop()

        if self.timer.isActive():
            self.timer.stop()
            self.timer.start()
        else:
            self.timer.start()

    def activate(self):
        #print("Activated")
        self.isActive = True
        self.countDown.start()
        if self.forceSpinBoxWidget:
            self.value = self.sb_hours.value() * 60 * 60 + self.sb_minutes.value() * 60
        else:
            self.value = self.sb_hours_value.read().toInt()[0] * 60 * 60 + self.sb_minutes_value.read().toInt()[0] * 60

    def check(self):
        #print("check")
        self.value -= 1
        if self.value == 0:
            #print("Der Timer ist abgelaufen")
            self.bomb_text.write(" Boom!")
            self.sleepTimerelapsed.emit()
            self.countDown.stop()
            self.isActive = False
        elif self.value == 10:
            self.sleepTimertenseconds.emit()
        else:
            m, s = divmod(self.value, 60)
            h, m = divmod(m, 60)
            text = "%02d:%02d:%02d" % (h, m, s)
            #self.lbl_countdown.setText(text)
            self.bomb_text.write(text)
            self.blockValueSignal = True
            if self.forceSpinBoxWidget:
                self.sb_hours.setValue(h)
                self.sb_minutes.setValue(m)
            else:
                self.sb_minutes_value.write(m)
                self.sb_hours_value.write(h)# = h
            self.blockValueSignal = False

    def stop(self, silent=True):
        if not silent:
            self.bomb_text.write("Abbruch")
        else:
            self.bomb_text.write("00:00:00")
        self.timer.stop()
        self.countDown.stop()
        self.blockValueSignal = True
        if self.forceSpinBoxWidget:
            self.sb_hours.setValue(0)
            self.sb_minutes.setValue(0)
        else:
            self.sb_minutes_value.write(0)
            self.sb_hours_value.write(0)
        self.blockValueSignal = False
        self.isActive = False


class LeadingZeroSpinBox(QSpinBox):

    def __init__(self, *args):

        QSpinBox.__init__(self, *args)
        self.setFocusPolicy(Qt.NoFocus)
        self.setMinimumSize(QSize(70, 40))
        self.setMaximumSize(QSize(90, 60))
        tmpFont = QFont()
        tmpFont.setPointSize(23)
        self.setFont(tmpFont)
        tmpLE = QLineEdit()
        tmpLE.setReadOnly(True)
        tmpLE.setFocusPolicy(Qt.NoFocus)
        self.setLineEdit(tmpLE)
        self.connect(self, SIGNAL("valueChanged(int)"), self.onSpinBoxValueChanged, Qt.QueuedConnection)

    def onSpinBoxValueChanged(self):
        # dont select the values when arrows are pressed (avoid highlighting)
        self.findChild(QLineEdit).deselect()

    def textFromValue(self, value):
        return "%02d" % value

def main():
    print("NOW Received")


if __name__ == "__main__":
    app = QApplication([])
    myWindow = SleepTimer()
    myWindow.sleepTimerelapsed.connect(main)
    myWindow.show()
    app.exec_()
