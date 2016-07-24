# use PyQt to play an animated gif
# added buttons to start and stop animation
# tested with PyQt4.4 and Python 2.5
# also tested with PyQt4.5 and Python 3.0
# vegaseat
import sys 
# too lazy to keep track of QtCore or QtGui
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import res


CustomSize = QSize(72, 72)
#TODO: Enlarging of Mute and Standby-Button! It is too small ... @ RaspberryPi

class MuteButtonLabel(QWidget):

    def __init__(self, parent=None): 
        QWidget.__init__(self, parent) 
        #self.setFixedSize(CustomSize)
        self.movie_screen = QLabel()
        self.movie_screen.setFixedSize(CustomSize)
        self.movie_screen.setAlignment(Qt.AlignLeft)
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.movie_screen)
        self.setLayout(main_layout)
        self.muted = False

        #self.unmute() # this is for testpurpose only

        
    def unmute(self):
        """start animation"""
        self.movie = QMovie(":/unmute.gif", QByteArray(), self)
        self.movie.setScaledSize(CustomSize*0.7)
        self.movie.setCacheMode(QMovie.CacheAll)
        self.movie.setSpeed(100)
        self.movie_screen.setMovie(self.movie)
        self.muted = False
        #print("Emitted 'sig_unmute'")
        self.emit(SIGNAL("sig_unmute"))
        self.movie.start()

    def show_unmute(self):
        self.movie = QMovie(":/unmute.gif", QByteArray(), self)
        self.movie.setScaledSize(CustomSize*0.7)
        self.movie.setCacheMode(QMovie.CacheAll)
        self.movie.setSpeed(100)
        self.movie_screen.setMovie(self.movie)
        self.muted = False
        self.movie.start()

    def mute(self):
        """stop the animation"""
        self.movie = QMovie(":/mute.gif", QByteArray(), self)
        self.movie.setScaledSize(CustomSize*0.7)
        self.movie.setCacheMode(QMovie.CacheAll)
        self.movie.setSpeed(100)
        self.movie_screen.setMovie(self.movie)
        self.muted = True
        #print("Emitted 'sig_mute'")
        self.emit(SIGNAL("sig_mute"))
        self.movie.start()

    def toggleMute(self):
        if self.muted:
            self.unmute()
        else:
            self.mute()

    def mousePressEvent(self, QMouseEvent):

        self.toggleMute()

        QMouseEvent.accept()

class StandbyButtonLabel(QWidget):

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        self.presentationArea = QLabel(self)
        self.presentationArea.setScaledContents(True)
        self.presentationArea.setFixedSize(CustomSize*0.7)
        self.presentationArea.setAlignment(Qt.AlignCenter)
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.presentationArea)
        self.setLayout(main_layout)
        self.ON_logo = QPixmap(":/standby_on.png")
        self.OFF_logo = QPixmap(":/standby_off.png")
        self.state = None


    def setInitialState(self, state):
        if state == "off":
            #print("SetStandbyState to 'off'")
            self.presentationArea.setPixmap(self.OFF_logo)
            self.state = False
        elif state == "on":
            #print("SetStandbyState to 'on'")
            self.presentationArea.setPixmap(self.ON_logo)
            self.state = True
        else:
            raise AttributeError("Possible States are 'on' and 'off' given as str")

    def toggleState(self):
        if self.state is None:
            #print("DEGUB: Initial State must be set first (.setInitialState('on/off')")
            return False
        if self.state is True:
            self.standby_off()
        else:
            self.standby_on()

    def standby_off(self):
        self.presentationArea.setPixmap(self.OFF_logo)
        self.emit(SIGNAL("sig_standby_off"))
        self.state = False
        #print("Signal 'sig_standby_off' was emitted")

    def standby_on(self):
        self.presentationArea.setPixmap(self.ON_logo)
        self.emit(SIGNAL("sig_standby_on"))
        self.state = True
        #print("Signal 'sig_standby_on' was emitted")

    def mousePressEvent(self, QMouseEvent):
        self.toggleState()
        QMouseEvent.accept()




if __name__ == "__main__":
    app = QApplication(sys.argv)
    player = StandbyButtonLabel()
    player.setInitialState("on")
    player.show()
    sys.exit(app.exec_())