#!/usr/bin/env python
# -*- coding: utf-8 -*

import ConfigParser
import argparse
import commands
import hashlib
import logging
import logging.handlers
import os
import pickle
import signal
import subprocess as sp
import sys
import time
import urllib
import importlib
import shutil

from PyQt4.QtCore import QString, QSize, Qt, SIGNAL, QSettings, QTime, QTimer, QDir, pyqtSlot, QObject, QEvent, \
    QThread, QLocale, QTranslator, QLibraryInfo, QChar
from PyQt4.QtGui import QIcon, QMainWindow, QFont, QAbstractItemView, QCursor, QDesktopWidget, QPixmap, \
    QListWidgetItem, QMessageBox, QSplashScreen, QPushButton, QMovie, QApplication, QVBoxLayout, QFileIconProvider, \
    QDialog

from lib import global_vars
from lib.LM_Widgets_scaled_contents import Scaling_QLabel
from lib.flickercharm import FlickCharm

_ = lambda x : x

parser = argparse.ArgumentParser(description='*** Raspi Webradio ***  by Matthias Laumer')
parser.add_argument('--no-network-check', action='store_true', help='Ignore missing network connection')
parser.add_argument('--debug', action='store_true', help='Show debug messages')
parser.add_argument('--disable-gpio', action='store_true', help='Disables GPIOs (Only available on Raspberry Pi)')
parser.add_argument('--fullscreen', action='store_true', help='Shows Window in Full-Screen Mode')
parser.add_argument('--touchscreen', action='store_true', help='disables visible mouse-pointer')
args = parser.parse_args()

cwd = os.path.dirname(os.path.realpath(__file__))      # gives the path, where the script is located
def read_conf(filepath, extention=".ini"):
    '''
    Reading a ini-like configuration-File and return it in a dict. {section:{option:value}}
    :param filepath: absolute filepath to the configuration-file
    :param extention: ".ini", ".conf", ".whatever"
    :return: Dict {'General': {'second': '1', 'thisisabool': True, 'key': '"value"'}}
    '''

    if not os.path.exists(filepath):
        logger.error(_('Configuration-File "{0}" does not exist').format(filepath))
        return False
    else:
        basename = os.path.basename(filepath)

    logger.info(_('Reading Configuration-File "{0}"').format(basename))
    if not os.path.isfile(filepath):
        logger.error(_('Configuration "{0}" does not exist or can not be accessed.').format(basename))
        raise IOError

    if not os.path.splitext(filepath)[1] == extention:
        logger.error(_('Configuration-File "{0}" has wrong file-format (need {1})').format(basename, extention))
        raise IOError
    target = {}
    try:
        config = ConfigParser.RawConfigParser(allow_no_value=False)
        config.read(filepath)
        sections = config.sections()
        for section in sections:
            target.setdefault(section, {})
            options = config.options(section)
            for option in options:
                try:
                    # this is the Value
                    tempopt = config.get(section, option)
                    # Check if the value should be a boolian Value... and convert if necessary
                    if tempopt in ["true", "True", "TRUE"]:
                        logger.debug(_("Convert value '{0}' from Option {1} to bool").format(tempopt, option))
                        tempopt = True
                    elif tempopt in ["false", "False", "FALSE"]:
                        logger.debug(_("Convert value '{0}' from Option {1} to bool").format(tempopt, option))
                        tempopt = False
                    elif tempopt in [None, ""]:
                        logger.debug(_("Setting Value '{0}' from Option {1} to None-Type").format(tempopt, option))
                        tempopt = None

                    target[section][option] = tempopt
                except:
                    e = sys.exc_info()[0]
                    logger.error(_("exception on {0} with {1}! Will override this with 'None-Type'").format(option, e))
                    target[section][option] = None
        logger.info(_("Reading Configurations-File complete."))
        return target
    except:
        e = sys.exc_info()[0]
        logger.error(_("Configuration {0} can not be read! Error: {1}").format(filepath, e))
        raise IOError

def write_conf(filepath, section="", option="", value="", extention=".ini"):
    '''
    Reading a ini-like configuration-File and return it in a dict. {section:{option:value}}
    :param filepath: absolute filepath to the configuration-file
    :param extention: ".ini", ".conf", ".whatever"
    :return: Dict {'General': {'second': '1', 'thisisabool': True, 'key': '"value"'}}
    '''

    if not os.path.exists(filepath):
        logger.error(_('Configuration-File "{0}" does not exist').format(filepath))
        return False
    else:
        basename = os.path.basename(filepath)

    logger.info(_('Wrinting Configuration-File "{0}"').format(basename))
    if not os.path.isfile(filepath):
        logger.error(_('Configuration "{0}" does not exist or can not be accessed.').format(basename))
        raise IOError

    if not os.path.splitext(filepath)[1] == extention:
        logger.error(_('Configuration-File "{0}" has wrong file-format (need {1})').format(basename, extention))
        raise IOError
    try:
        config = ConfigParser.RawConfigParser(allow_no_value=False)
        config.read(filepath)
        config.set(section, option, value)
        # Writing our configuration file
        with open(filepath, 'wb') as configfile:
            config.write(configfile)
    except:
        e = sys.exc_info()[0]
        logger.error(_("Configuration {0} can not be written! Error: {1}").format(filepath, e))
        raise IOError

def setupLogger(console=True, File=False, Variable=False, Filebackupcount=0):
    '''
    Setup a logger for the application
    :return: Nothing
    '''
    global logger
    global log_capture_string
    # create logger
    logging.raiseExceptions = False
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(filename)s - %(funcName)s - %(message)s')
    # Check if log exists and should therefore be rolled
    needRoll = os.path.isfile(LOG_FILENAME)

    if File:
        # create file handler which logs even debug messages and hold a backup of old logs
        fh = logging.handlers.RotatingFileHandler( LOG_FILENAME, backupCount=int(Filebackupcount)) # create a backup of the log
        fh.setLevel(logging.DEBUG) if args.debug else fh.setLevel(logging.INFO)  #TODO:Change this to ERROR after dev
        fh.setFormatter(formatter)
        logger.addHandler(fh)
    if Variable:
        # create variable handler for on the fly read
        vh = logging.StreamHandler(log_capture_string)
        vh.setLevel(logging.DEBUG) if args.debug else vh.setLevel(logging.INFO)
        vh.setFormatter(formatter)
        logger.addHandler(vh)
    if console:
        # create console handler with a higher log level
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG) if args.debug else ch.setLevel(logging.ERROR)
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    # This is a stale log, so roll it
    if File and needRoll:
        # Add timestamp
        logger.debug(_('\n---------\nLog closed on {0}.\n---------\n').format(time.asctime()))
        # Roll over on application start
        logger.handlers[0].doRollover()
    # Add timestamp
    logger.debug(_('\n---------\nLog started on {0}.\n---------\n').format(time.asctime()))

def excepthook(excType, excValue, traceback):
    global logger
    logger.error("Uncaught exception",
                 exc_info=(excType, excValue, traceback))

def sigint_handler(*args):
    '''
    This handler is called whenever Python receives a "sigint" signal (CTRL+C)
    :param args: NOT IN USE
    :return: Nothong, Exits the programm with exit-code 0 (success)
    '''

    logger.debug(_("SigTerm received... savely shut down now."))
    mainwindow.close()
    logger.debug(_("Final Actions successfully performed."))
    sys.exit(0)

signal.signal(signal.SIGINT, sigint_handler)

################################ Prepare Logger ######################################
logger = logging.getLogger("webradio")
LOG_FILENAME = "webradio.log"
setupLogger(console=True, File=True, Filebackupcount=1, Variable=False)
sys.excepthook = excepthook

if args.disable_gpio:
    GPIO_active = False
###################### Read Configuration-File (webradio.conf) #######################
if os.path.isfile(os.path.join(cwd, "webradio.conf")):
    global_vars.configuration = read_conf(os.path.join(cwd, "webradio.conf"), ".conf")
else:
    global_vars.configuration = read_conf(os.path.join(cwd, "webradio_fallback.conf"), ".conf")
    shutil.copyfile(os.path.join(cwd, "webradio_fallback.conf"), os.path.join(cwd, "webradio.conf"))


###################### IMPORTS #######################################################

from lib.radio_station_finder import RadioDeApi
logger.info(u"Running with Screen-Resolution {0}".format(global_vars.configuration.get("GENERAL").get("screen_resolution")))
from ui.flex import Ui_MainWindow
from lib.players import MPC_Player
from lib.virt_keyboard import VirtualKeyboard
from lib.weather_widget import weather_widget
from lib.button_labels import MuteButtonLabel, StandbyButtonLabel
from lib.mpd_daemon import MPD_Eventlistener
from lib.usb_manager import USB_manager
from lib.mpd_filesystemView import LM_QFileSystemModel
from lib.system_test import test_onlineServices as systemtest
# loading the defined design from the global vars and import the resource-file load fallback if there is nothing
# specified...
if global_vars.configuration.get("GENERAL").get("design") is not None:
    logger.info("Loadinging Design: {0}".format(global_vars.configuration.get("GENERAL").get("design")))
    if os.path.isfile(os.path.join(cwd, "res", "designs", global_vars.configuration.get("GENERAL").get("design"),
                                   "res.py")):
        try:
            #__import__("res.designs.{0}.res".format(global_vars.configuration.get("GENERAL").get("design")))
            res = importlib.import_module(".res",
                    package="res.designs.{0}".format(global_vars.configuration.get("GENERAL").get("design")))
        except ImportError:
            logger.error("Error: Design can not be loaded!, Loading Fallback!")
            try:
                res = importlib.import_module(".res",
                    package="res.designs.fallback")
            except ImportError:
                logger.error("Fallback can not be loaded! Aborting.")
                raise ImportError
            else:
                # assure that right stylesheet is loaded if the user-design has failed to load...
                global_vars.configuration.get("GENERAL").update({"design": "fallback"})
    else:
        logger.error("Specified Design does not exist on this machine! Loading fallback")
        try:
            res = importlib.import_module(".res",
                    package="res.designs.fallback")
        except ImportError:
            logger.error("Fallback can not be loaded! Aborting.")
            raise ImportError
        else:
            # assure that right stylesheet is loaded if the user-design has failed to load...
            global_vars.configuration.get("GENERAL").update({"design": "fallback"})
else:
    logger.info("No Design-Specification found in current config-file, Loading Fallback.")
    try:
        res = importlib.import_module(".res",
                package="res.designs.fallback")
    except ImportError:
        logger.error("Fallback can not be loaded! Aborting.")
        raise ImportError
    else:
        # assure that right stylesheet is loaded if the user-design has failed to load...
        global_vars.configuration.get("GENERAL").update({"design": "fallback"})

from lib.lastFM_AlbumArtGrabber import LastFMDownloader
from lib.gpio_simulator import GPIO_Simulator

try:  # try to load the GPIO Watchdog. If not executed at a raspberry pi or no Rpi.GPIO library is installed ...
    from lib.gpio_watchdog import Gpio_Watchdog

    GPIO_active = True if os.geteuid() == 0 else False  # also check if script was started as root-user
    MusicFolder = global_vars.configuration.get("GENERAL").get("musicfolder")
    VARIABLE_DATABASE = global_vars.configuration.get("GENERAL").get("variable_database_name")
    if not GPIO_active:
        logger.warning("GPIOs can not be used, because root-privileges are required to do this!")
except ImportError:  # load the GPIO simulator instead. The signals are the same than from the GPIO watchdog .....
    logger.warning("GPIO Watchdog was not found or can not run at this machine")
    GPIO_active = False
    MusicFolder = global_vars.configuration.get("DEVELOPMENT").get("musicfolder")
    VARIABLE_DATABASE = global_vars.configuration.get("DEVELOPMENT").get("variable_database_name")

__version__ = "0.2.3"

BasenameFavoritesPlaylist = "favorites"
LogoFolder = os.path.join(cwd, "Logos")
AlbumArtFolder = os.path.join(cwd, "Albumart")

try:
    _fromUtf8 = str
except AttributeError:
    def _fromUtf8(s):
        return s


class MainWindow(QMainWindow, Ui_MainWindow):

    def __init__(self, size, parent=None):

        super(MainWindow, self).__init__(parent)
        logger.info("Init.")
        self.setFixedSize(size)
        self.setupUi(self)
        app.processEvents()
        #self.startup_actions()
        logger.info("Init sucessfull.")

    def reRead_config(self):
        global_vars.configuration = read_conf(os.path.join(cwd, "webradio.conf"), ".conf")

    def startup_actions(self, presetting=False):

        def __define_additional_widgets(self):
            #print("mpd_listener",QTime.currentTime())
            self.mpd_listener = MPD_Eventlistener()
            #print("Done",QTime.currentTime())
            #print("usb-manager",QTime.currentTime())
            self.usb_manager = USB_manager(global_vars.configuration.get("GENERAL").get("variable_database_mountpoint"))
            #print("Done",QTime.currentTime())
            if GPIO_active:
                self.gpio_watchdog = Gpio_Watchdog()
            else:
                self.gpio_watchdog = GPIO_Simulator()
                if not args.disable_gpio:
                    self.gpio_watchdog.show()

            #print("VirtKeyboard",QTime.currentTime())
            self.virtualKeyboard = VirtualKeyboard()
            self.virtualKeyboard2 = VirtualKeyboard()
            #print("Done",QTime.currentTime())
            self.stackedWidget.addWidget(self.virtualKeyboard)
            self.stackedWidget_2.addWidget(self.virtualKeyboard2)  #index 4
            #self.weatherWidget = weather_widget(self.tab)
            self.weatherWidget = weather_widget(cwd, parent=self)
            layout_temp = QVBoxLayout(self.tab)
            layout_temp.addWidget(self.weatherWidget)

            self.widget_Mute = MuteButtonLabel(self)
            self.widget_Mute.setFixedSize(QSize(60, 60))
            tmplayout1 = QVBoxLayout()
            tmplayout1.addWidget(self.widget_Mute)
            self.widget_Mute_1.setLayout(tmplayout1)
            #self.widget_Mute.setGeometry(QRect(0, 480, 80, 80))

            self.widget_Standby = StandbyButtonLabel(self)
            self.widget_Standby.setFixedSize(QSize(60,60))
            tmplayout2 = QVBoxLayout()
            tmplayout2.addWidget(self.widget_Standby)
            self.widget_Mute_2.setLayout(tmplayout2)
            #self.widget_Standby.setGeometry(QRect(90, 490, 75, 75))

            self.button_pressed = None
            self.audio_amp_isActive = False
            self.shutdowntrigger = False
            #print("Rest is Done",QTime.currentTime())
            self.splash = AnimatedSplashScreen(":/loading.gif")
            self.charm = FlickCharm()

        def __define_widgets_presettings(self):

            self.widget_Standby.setInitialState("off")
            logger.info("Loading Stylesheet: {0}".format(os.path.join(cwd, "res", "designs", global_vars.configuration.get("GENERAL").get("design"),
                                       "stylesheet.qss")))
            try:
                with open(os.path.join(cwd, "res", "designs", global_vars.configuration.get("GENERAL").get("design"),
                                       "stylesheet.qss")) as style:
                    stylenew = style.read()
                self.setStyleSheet(stylenew)
            except:
                logger.error("Stylesheet can not be loaded! Aborting.")
                raise ImportError

            self.lbl_Senderlogo.setText("")
            self.label.setText("")
            self.lbl_Fav.setText("")
            self.lbl_Fav.installEventFilter(self)
            self.installEventFilter(self)
            self.lbl_Sendername.setText(self.tr("Welcome !"))
            self.lbl_Musiktitel.setText(self.tr("please 'search' to be able to play a station"))
            self.pBZurueck.setVisible(False)
            font = QFont()
            font.setPointSize(26)
            self.lW_in_ihrer_naehe.setFont(font)      #schriftgroesse 26 (font)
            self.charm.activateOn(self.lW_in_ihrer_naehe)
            self.lW_sendervorschlaege.setFont(font)   #schriftgroesse 26 (font)
            self.charm.activateOn(self.lW_sendervorschlaege)
            self.lW_kategorievorschlaege.setFont(font)#schriftgroesse 26 (font)
            self.charm.activateOn(self.lW_kategorievorschlaege)
            self.lW_stationen_nach_cat.setFont(font)  #schriftgroesse 26 (font)
            self.charm.activateOn(self.lW_stationen_nach_cat)
            self.listWidget.setFont(font)
            self.listWidget.setIconSize(QSize(35,35))
            self.charm.activateOn(self.listWidget)

            self.lbl_albumArt.setScaledContents(True)

            self.tabWidget_main.setIconSize(QSize(40,40))
            self.tabWidget_main.setTabIcon(0, QIcon(":/radio.png"))
            self.tabWidget_main.setTabText(0,"")

            self.tabWidget_main.setTabIcon(1, QIcon(":/media.png"))
            self.tabWidget_main.setTabText(1, "")

            self.tabWidget_main.setTabIcon(2, QIcon(":/weather.png"))
            self.tabWidget_main.setTabText(2, "")

            self.tabWidget_main.setTabIcon(3, QIcon(":/clock.png"))
            self.tabWidget_main.setTabText(3, "")

            self.tabWidget_main.setTabIcon(4, QIcon(":/config.png"))
            self.tabWidget_main.setTabText(4, "")

            self.slider_vol.setMinimum(0)
            self.slider_vol.setMaximum(100)
            self.slider_vol.setSingleStep(5)    # this have only effect if the slider is moved with arrow-keys
            self.slider_vol.setTickInterval(5)  # puly dont know....
            self.slider_vol.setPageStep(20)
            self.slider_vol.setFocusPolicy(Qt.NoFocus)

            self.pBVol_down.setText("")
            self.pBVol_down.setIcon(QIcon(":/volume_down.png"))
            self.pBVol_down.setIconSize(self.pBVol_down.sizeHint()*1.4)
            self.pBVol_down.setFocusPolicy(Qt.NoFocus)

            self.pBVol_up.setText("")
            self.pBVol_up.setIcon(QIcon(":/volume_up.png"))
            self.pBVol_up.setIconSize(self.pBVol_up.sizeHint()*1.4)
            self.pBVol_up.setFocusPolicy(Qt.NoFocus)

            self.pBFavoriten.setText("")
            self.pBFavoriten.setIconSize(self.pBFavoriten.sizeHint()*2)
            self.pBFavoriten.setFocusPolicy(Qt.NoFocus)

            self.pBZurueck.setText("")
            self.pBZurueck.setIconSize(self.pBZurueck.sizeHint()*2)
            self.pBZurueck.setFocusPolicy(Qt.NoFocus)

            self.pBSuchen.setText("")
            self.pBSuchen.setIconSize(self.pBSuchen.sizeHint()*2)
            self.pBSuchen.setFocusPolicy(Qt.NoFocus)

            self.pBHome.setText("")
            self.pBHome.setIconSize(self.pBHome.sizeHint()*2)
            self.pBHome.setFocusPolicy(Qt.NoFocus)

            self.pB_move_down.setFocusPolicy(Qt.NoFocus)
            self.pB_add_to_playlist.setFocusPolicy(Qt.NoFocus)
            self.pB_relead_tree.setFocusPolicy(Qt.NoFocus)
            self.pB_add_on_playlist.setFocusPolicy(Qt.NoFocus)
            self.pB_add_to_playlist_2.setFocusPolicy(Qt.NoFocus)
            self.pB_Audio_back.setFocusPolicy(Qt.NoFocus)
            self.pB_Audio_back_2.setFocusPolicy(Qt.NoFocus)
            self.pB_Audio_forward.setFocusPolicy(Qt.NoFocus)
            self.pB_Audio_forward_2.setFocusPolicy(Qt.NoFocus)
            self.pB_Audio_play_pause.setFocusPolicy(Qt.NoFocus)
            self.pB_Audio_play_pause_2.setFocusPolicy(Qt.NoFocus)
            self.pB_Audio_stop.setFocusPolicy(Qt.NoFocus)
            self.pB_Audio_stop_2.setFocusPolicy(Qt.NoFocus)
            self.pB_del_from_playlist.setFocusPolicy(Qt.NoFocus)
            self.pB_in_ihrer_naehe.setFocusPolicy(Qt.NoFocus)
            self.pB_Sendervorschlaege_fuer_sie.setFocusPolicy(Qt.NoFocus)
            self.pB_move_down.setFocusPolicy(Qt.NoFocus)
            self.pB_move_down_2.setFocusPolicy(Qt.NoFocus)
            self.pB_nach_Genre.setFocusPolicy(Qt.NoFocus)
            self.pB_nach_Land.setFocusPolicy(Qt.NoFocus)
            self.pB_nach_Sprache.setFocusPolicy(Qt.NoFocus)
            self.pB_nach_Stadt.setFocusPolicy(Qt.NoFocus)
            self.pB_nach_Thema.setFocusPolicy(Qt.NoFocus)
            self.pB_sender_nach_kategorie.setFocusPolicy(Qt.NoFocus)
            self.pB_sender_suchen.setFocusPolicy(Qt.NoFocus)


            self.pB_Audio_play_pause.setText("")
            self.pB_Audio_play_pause.setIcon(QIcon(":/play.png"))
            self.pB_Audio_play_pause.setIconSize(self.pB_Audio_play_pause.sizeHint()*2)
            self.pB_Audio_play_pause.setFocusPolicy(Qt.NoFocus)

            self.pB_Audio_stop.setText("")
            self.pB_Audio_stop.setIcon(QIcon(":/stop.png"))
            self.pB_Audio_stop.setIconSize(self.pB_Audio_stop.sizeHint()*2)
            self.pB_Audio_stop.setFocusPolicy(Qt.NoFocus)

            self.pB_Audio_back.setText("")
            self.pB_Audio_back.setIcon(QIcon(":/backward.png"))
            self.pB_Audio_back.setIconSize(self.pB_Audio_back.sizeHint()*2)
            self.pB_Audio_back.setFocusPolicy(Qt.NoFocus)

            self.pB_Audio_forward.setText("")
            self.pB_Audio_forward.setIcon(QIcon(":/next.png"))
            self.pB_Audio_forward.setIconSize(self.pB_Audio_forward.sizeHint()*2)
            self.pB_Audio_forward.setFocusPolicy(Qt.NoFocus)
            ########################################
            self.pB_Audio_play_pause_2.setText("")
            self.pB_Audio_play_pause_2.setIcon(QIcon(":/play.png"))
            self.pB_Audio_play_pause_2.setIconSize(self.pB_Audio_play_pause_2.sizeHint()*2)
            self.pB_Audio_play_pause_2.setFocusPolicy(Qt.NoFocus)

            self.pB_Audio_stop_2.setText("")
            self.pB_Audio_stop_2.setIcon(QIcon(":/stop.png"))
            self.pB_Audio_stop_2.setIconSize(self.pB_Audio_stop_2.sizeHint()*2)
            self.pB_Audio_stop_2.setFocusPolicy(Qt.NoFocus)

            self.pB_Audio_back_2.setText("")
            self.pB_Audio_back_2.setIcon(QIcon(":/backward.png"))
            self.pB_Audio_back_2.setIconSize(self.pB_Audio_back_2.sizeHint()*2)
            self.pB_Audio_back_2.setFocusPolicy(Qt.NoFocus)

            self.pB_Audio_forward_2.setText("")
            self.pB_Audio_forward_2.setIcon(QIcon(":/next.png"))
            self.pB_Audio_forward_2.setIconSize(self.pB_Audio_forward_2.sizeHint()*2)
            self.pB_Audio_forward_2.setFocusPolicy(Qt.NoFocus)
            ############################################
            self.pB_relead_tree.setText("")
            self.pB_relead_tree.setIcon(QIcon(":/refresh.png"))
            self.pB_relead_tree.setIconSize(self.pB_relead_tree.sizeHint()*2)
            self.pB_relead_tree.setFocusPolicy(Qt.NoFocus)

            self.pB_autorepeat.setText("")
            self.pB_autorepeat.setIcon(QIcon(":/repeat.png"))
            self.pB_autorepeat.setIconSize(self.pB_autorepeat.sizeHint()*2)
            #self.pB_autorepeat.setFocusPolicy(Qt.NoFocus)

            self.pB_autorepeat_2.setText("")
            self.pB_autorepeat_2.setIcon(QIcon(":/repeat.png"))
            self.pB_autorepeat_2.setIconSize(self.pB_autorepeat_2.sizeHint()*2)
            #self.pB_autorepeat_2.setFocusPolicy(Qt.NoFocus)

            self.pB_markAll.setText("")
            self.pB_markAll.setIcon(QIcon(":/selectall.png"))
            self.pB_markAll.setIconSize(self.pB_markAll.sizeHint()*2)
            self.pB_markAll.setFocusPolicy(Qt.NoFocus)

            self.pB_add_to_playlist.setText("")
            self.pB_add_to_playlist.setIcon(QIcon(":/add.png"))
            self.pB_add_to_playlist.setIconSize(self.pB_add_to_playlist.sizeHint()*1.7)
            self.pB_add_to_playlist.setFocusPolicy(Qt.NoFocus)

            self.pB_add_to_playlist_2.setText("")
            self.pB_add_to_playlist_2.setIcon(QIcon(":/add.png"))
            self.pB_add_to_playlist_2.setIconSize(self.pB_add_to_playlist.sizeHint()*1.7)
            self.pB_add_to_playlist_2.setFocusPolicy(Qt.NoFocus)
            ##########
            ##########
            self.pB_move_down_2.setText("")
            self.pB_move_down_2.setIcon(QIcon(":/up.png"))
            self.pB_move_down_2.setIconSize(self.pB_move_down_2.sizeHint()*2)
            self.pB_move_down_2.setFocusPolicy(Qt.NoFocus)

            self.pB_del_from_playlist.setText("")
            self.pB_del_from_playlist.setIcon(QIcon(":/del.png"))
            self.pB_del_from_playlist.setIconSize(self.pB_del_from_playlist.sizeHint()*1.7)
            self.pB_del_from_playlist.setFocusPolicy(Qt.NoFocus)

            self.pB_add_on_playlist.setText("")
            self.pB_add_on_playlist.setIcon(QIcon(":/add.png"))
            self.pB_add_on_playlist.setIconSize(self.pB_add_on_playlist.sizeHint()*1.7)
            self.pB_add_on_playlist.setFocusPolicy(Qt.NoFocus)

            self.pB_move_down.setText("")
            self.pB_move_down.setIcon(QIcon(":/down.png"))
            self.pB_move_down.setIconSize(self.pB_move_down.sizeHint()*2)
            self.pB_move_down.setFocusPolicy(Qt.NoFocus)
            ######
            self.treeView.setSelectionMode(QAbstractItemView.MultiSelection)
            #self.treeView.setIconSize(QSize(64,64))
            self.charm.activateOn(self.treeView)
            self.charm.activateOn(self.treeWidget_2)

            #populating cB for Design-Changes with possibilities and set the current Index
            content = os.listdir(os.path.join(cwd, "res", "designs"))
            self.cB_design.clear() # empty existing items (if function is called from Design-Change)
            self.cB_design.addItems([i for i in content if not i.endswith(".pyc") and not i.endswith(".py")])
            index = self.cB_design.findText(global_vars.configuration.get("GENERAL").get("design"),
                                            Qt.MatchFixedString)
            if index >= 0:
                 self.cB_design.setCurrentIndex(index)

        def __setConnections(self):

            ##################################################################################    GLOBAL CONNECTIONS
            #print("Setup Connections...")
            self.connect(self, SIGNAL("start_loading"), lambda: self.splash_loading(True))
            self.connect(self, SIGNAL("stop_loading"), self.splash_loading)
            self.connect(self.treeWidget_2, SIGNAL("start_loading"), lambda: self.splash_loading(True))
            self.connect(self.treeWidget_2, SIGNAL("stop_loading"), self.splash_loading)
            self.connect(self.weatherWidget, SIGNAL("start_loading"), lambda: self.splash_loading(True))
            self.connect(self.weatherWidget, SIGNAL("stop_loading"), self.splash_loading)
            self.tabWidget_main.currentChanged.connect(self.on_tabIndexChanged)
            self.connect(self.widget_Mute, SIGNAL("sig_mute"), self.mute)
            self.connect(self.widget_Mute, SIGNAL("sig_unmute"), self.unmute)
            self.connect(self.widget_Standby, SIGNAL("sig_standby_on"), self.unmute)
            self.connect(self.widget_Standby, SIGNAL("sig_standby_off"), self.standby)
            self.connect(self.mpd_listener, SIGNAL("sig_mpd_statusChanged"), self.on_statusChanged)
            self.connect(self.mpd_listener, SIGNAL("sig_mpd_volumeChanged"), self.on_volumeChanged)
            self.connect(self.mpd_listener, SIGNAL("sig_mpd_media_local_changed"), self.on_media_local_changed)
            self.connect(self.usb_manager, SIGNAL("sig_usb_disconnected"), self.on_usb_disconnected)
            self.connect(self.usb_manager, SIGNAL("sig_usb_connected"), self.on_usb_connected)
            self.connect(self.pBVol_up, SIGNAL("clicked()"), lambda : self.on_volumeChanged(relativeVol="+5"))
            self.connect(self.pBVol_down, SIGNAL("clicked()"), lambda : self.on_volumeChanged(relativeVol="-5"))
            self.connect(self, SIGNAL("sig_favorites_changed"), self.onFavoritesChanged)
            self.slider_vol.valueChanged.connect(self.on_volumeChanged) # this will fire a lot of signals if moved....
            self.tabWidget_main.currentChanged.connect(self.checkHeaders)
            self.stackedWidget.currentChanged.connect(self.checkHeaders)
            self.stackedWidget_2.currentChanged.connect(self.checkHeaders)

            self.connect(self.mpd_listener, SIGNAL("sig_mpd_stationChanged"), self.on_currentStationChanged)
            self.connect(self, SIGNAL("STATUS"),self.showStatusBarText)

            self.connect(self.gpio_watchdog, SIGNAL('gpio_button_pressed'), self.signalreader_buttons_on) #overloaded
            self.connect(self.gpio_watchdog, SIGNAL('gpio_button_released'), self.signalreader_buttons_off)#overloaded
            self.connect(self.gpio_watchdog, SIGNAL("gpio_rotary_turned"), self.signalreader_rotary) #overloaded
            self.connect(self.gpio_watchdog, SIGNAL("gpio_temperature"), self.signalreader_temp) #overloaded
            #self.connect(self.gpio_watchdog, SIGNAL("gpio_rotary_button_pressed"), self.signalreader_rotary_btn)
            self.connect(self, SIGNAL("sig_audio_amp_on"), self.on_audio_amp_on)
            self.connect(self, SIGNAL("sig_audio_amp_off"), self.on_audio_amp_off)
            self.connect(self, SIGNAL("sig_status_on"), self.statusLED_on)
            self.connect(self, SIGNAL("sig_status_off"), self.statusLED_off)
            self.connect(self, SIGNAL("sig_LCD_off"), self.LCD_off)
            self.connect(self, SIGNAL("sig_LCD_on"), self.LCD_on)
            #################################################################################         page 1

            self.pB_in_ihrer_naehe.clicked.connect(self.onInIhrerNaehe)
            self.pB_Sendervorschlaege_fuer_sie.clicked.connect(self.onSendervorschlaege)
            self.pB_sender_nach_kategorie.clicked.connect(lambda : self.stackedWidget.setCurrentIndex(4))
            self.pB_sender_suchen.clicked.connect(self.onCustomSearch)

            #################################################################################         page 2
            self.lW_in_ihrer_naehe.itemPressed.connect(self.onItemClicked)

            #################################################################################         page 3
            self.lW_sendervorschlaege.itemPressed.connect(self.onItemClicked)

            #################################################################################         page 4
            #  'genre', 'topic', 'country', 'city', 'language',
            self.pB_nach_Genre.clicked.connect(lambda : self.onCatSearch("genre"))
            self.pB_nach_Land.clicked.connect(lambda : self.onCatSearch("country"))
            self.pB_nach_Stadt.clicked.connect(lambda : self.onCatSearch("city"))
            self.pB_nach_Sprache.clicked.connect(lambda : self.onCatSearch("language"))
            self.pB_nach_Thema.clicked.connect(lambda : self.onCatSearch("topic"))

            #################################################################################         page 5
            # Results for selected category
            self.lW_kategorievorschlaege.itemPressed.connect(self.onCatChosen)

            #################################################################################         page 6
            # this sheet (index 6) can also be used to display other lists ...
            self.lW_stationen_nach_cat.itemPressed.connect(self.onItemClicked)

            #################################################################################         page 7
            self.connect(self.virtualKeyboard, SIGNAL("sigInputString"), self.onCustomSearch_OK)
            self.connect(self.virtualKeyboard2, SIGNAL("sigInputString"), self.onCustomSearch_media_OK)


            ################################################################################   Media-Buttons
            self.pB_Audio_play_pause.clicked.connect(lambda : self.mediaPlayerControl("play"))
            self.pB_Audio_stop.clicked.connect(lambda : self.mediaPlayerControl("stop"))
            self.pB_Audio_back.clicked.connect(lambda : self.mediaPlayerControl("back"))
            self.pB_Audio_forward.clicked.connect(lambda : self.mediaPlayerControl("next"))
            self.pB_Audio_play_pause_2.clicked.connect(lambda : self.mediaPlayerControl("play",True))
            self.pB_Audio_stop_2.clicked.connect(lambda : self.mediaPlayerControl("stop"))
            self.pB_Audio_back_2.clicked.connect(lambda : self.mediaPlayerControl("back"))
            self.pB_Audio_forward_2.clicked.connect(lambda : self.mediaPlayerControl("next"))

            self.pB_add_to_playlist.clicked.connect(self.add_from_tree)
            self.pB_add_to_playlist_2.clicked.connect(self.add_from_search)
            self.pB_autorepeat.clicked.connect(lambda : self.onAutoRepeat("1"))
            self.pB_autorepeat_2.clicked.connect(lambda : self.onAutoRepeat("2"))
            self.pB_markAll.clicked.connect(self.onSelectAll)

            ##################################################################################### Sleep-Timer
            self.widget_sleep_timer.sleepTimerelapsed.connect(self.onSleepTimerElapsed)
            self.widget_sleep_timer.sleepTimertenseconds.connect(self.onSleepTimerCloseToElapsed)

            ##################################################################################### Settings
            self.cB_design.currentIndexChanged.connect(self.setNewDesign)  # overloaded with new index.

        def __initial_variable_setup(self):
            self.currentIndex = self.stackedWidget.currentIndex()
            self.lastIndex = self.stackedWidget.currentIndex()
            self.playedLast = 0

            self.RadioDeAPI = RadioDeApi()
            self.player = None

            self.favorites = {}        # { id: instance(RadioStation), ... }
            self.myCurrentStation=None # if set, than it is a instance of "RadioStation"
            self.mode = "radio"
            self.volume = None
            self.blockSeekSlider = False
            self.__lastStateSeekSliderValue = 0
            self.broken_connections = []

        def __startup_fakeClock(self):

            self.worker = WorkerThread(self.fakeclock)
            self.worker.start()

        def __loadFavorites(self):
            basename = "favorites"
            extention = "fav"

            Openfile = os.path.join(cwd, "{0}.{1}".format(basename, extention))
            if os.path.isfile(Openfile):
                self.favorites = pickle.load(open(Openfile, "rb" ) )
                logger.info("Found Favorites: {0}".format(Openfile))
            else:
                logger.warning("No stored Favorites found.")
                self.favorites = {}

        def __loadGPIO_Presets(self):
            basename = "presets"
            extention = "fav"

            Openfile = os.path.join(cwd, "{0}.{1}".format(basename, extention))
            if os.path.isfile(Openfile):
                self.gpio_presets = pickle.load(open(Openfile, "rb" ) )
                logger.info("Found Presets: {0}".format(Openfile))
            else:
                logger.warning("No stored Presets found.")
                self.gpio_presets = {}

        def __readSettings(self):
            logger.info('Reading Settings')
            settings = QSettings("Laumer", "RapiRadio")

            selectedLastTab = settings.value("tab", "0")
            selectedLastTab = selectedLastTab.toInt()[0]
            self.tabWidget_main.setCurrentIndex(selectedLastTab)
            self.mode = "radio" if selectedLastTab == 0 else "media"

            playedLast = settings.value("last", "0")
            self.playedLast = playedLast.toInt()[0]
            self.switchModeTo(self.mode, self.mode)

            if self.playedLast > 0 and self.mode == "radio":
                self.playStationByID(self.playedLast)

        def __moveCenter(self):
            """
            Placing the windows in the middle of the screen
            """

            screen = QDesktopWidget().screenGeometry()
            size =  self.geometry()
            self.move((screen.width()-size.width())/2, (screen.height()-size.height())/2-27)

        if presetting:
            __define_widgets_presettings(self)
        else:
            __initial_variable_setup(self)
            __define_additional_widgets(self)
            __define_widgets_presettings(self)
            __setConnections(self)
            __startup_fakeClock(self)
            __loadFavorites(self)
            __loadGPIO_Presets(self)
            __moveCenter(self)

        if not args.no_network_check:
            logger.info("Checking Network")
            QTimer.singleShot(0,self.checkInternet)
        __readSettings(self)

        self.stackedWidget.setCurrentIndex(0)
        self.usb_manager.startup_notifier()
        if args.touchscreen:
            app.setOverrideCursor(QCursor(Qt.BlankCursor))     # new - testing
            self.setCursor(QCursor(Qt.BlankCursor))            # new - testing
        else:
            app.restoreOverrideCursor()
            self.unsetCursor()

    def fakeclock(self):
        """
        Function will update every 10 seconds the "clock" displayed (endless loop)
        The function is executed in a Worker-Thread
        """
        while True:
            thetime = QTime.currentTime()
            text = thetime.toString('hh:mm')
            completetext = (self.tr("Clock: %1").arg(text))
            self.lbl_Uhr.setText(completetext)
            time.sleep(10)

    def writeSettings(self):
        """
        Write Setting of that application. This is called during close-event
        """
        logger.info('Writing Settings')
        settings = QSettings("Laumer", "RapiRadio")
        if self.myCurrentStation is not None:
            settings.setValue("last", self.myCurrentStation.id)   # save last played station
        if self.mode == "radio":
            tabvalue = 0
        elif self.mode == "media":
            tabvalue = 1
        else:
            tabvalue = 0
        settings.setValue("tab", tabvalue)                        # save last tab which was selected

    def saveFavorites(self):
        """
        Save current favories in a dumped file on the HDD, the format is "{}".
        Also favorites will be saved in m3u format, in order to be able to call favories with a remote

        :return: [#STATION_ID \n http://url.for.mp3stream, ]
        """
        container = self.favorites
        favlist = []
        for key in self.favorites.iterkeys():
            favlist.append("#%d" %key)
            favlist.append(self.favorites[key].url)
        basename = "favorites"
        extention = "fav"

        filename = os.path.join(cwd, "{0}.{1}".format(basename, extention))

        try:
            pickle.dump(container, open(filename, "wb"))
        except IOError:
            logger.error("was not able to store favorites, maybe dont have got the file-permissions needed")
            return (False, [])
        logger.info("Stored Favorites to: {0}".format(filename))
        return (True, favlist)

    def saveGPIO_Presets(self):
        """
        Store Presets for GPIO Buttons, format is a "{}"
        {BUTTON_NO : STATION_ID}

        :return: True or False
        """
        container = self.gpio_presets
        basename = "presets"
        extention = "fav"

        filename = os.path.join(cwd, "{0}.{1}".format(basename, extention))

        try:
            pickle.dump(container, open(filename, "wb"))
        except IOError:
            logger.error("was not able to store presets, maybe dont have got the file-permissions needed")
            return False
        logger.info("Stored Presets to: {0}".format(filename))
        return True

    def writePlaylist(self, name, listOfContent):
        """
        Write a m3u playlist to a given name[.m3u] and fill it with the given list of Content, every item is written in
        a separate line into the file
        :param name: "favorites"
        :param listOfContent: [ "#2312", "http://url.to.mp3steam", "#2313", "http://next.url"]
        :return: True or False
        """
        basename = name
        extention = "m3u"
        logger.debug("Writing new Playlistcontent: {0}".format(listOfContent))
        filename = os.path.join(cwd, "{0}.{1}".format(basename, extention))
        try:
            with open(filename, "w") as playlistfile:
                for item in listOfContent:
                    playlistfile.write("%s\n" % item)
        except:
            return False
        return True

    def markAsFavorite(self, _bool=None):
        """
        Mark or dismark the current playing station as favorite, change the "star" in the right corner accordingly
        :param _bool: True, False, None
        :return: emit Signal "sig_favorites_changed" (which will trigger the storage as dict and as m3u file)
        """
        if _bool:
            self.lbl_Fav.setPixmap(QPixmap(":/fav.png"))
            app.processEvents()
        elif _bool is None:
            if self.myCurrentStation != None:
                if self.myCurrentStation.id in self.favorites.keys():
                    logger.info("Remove {0} from Favorites".format(self.myCurrentStation.name.encode("utf-8")))
                    self.myCurrentStation.unsetFavorite()
                    self.favorites.pop(self.myCurrentStation.id)
                    self.lbl_Fav.setPixmap(QPixmap(":/fav_empty.png"))
                    app.processEvents()
                else:
                    logger.info("Add {0} to favorites".format(self.myCurrentStation.name.encode("utf-8")))
                    self.myCurrentStation.setAsFavorite()
                    self.favorites.update({self.myCurrentStation.id: self.myCurrentStation})
                    self.lbl_Fav.setPixmap(QPixmap(":/fav.png"))
                    app.processEvents()
                self.emit(SIGNAL("sig_favorites_changed"))
        else:
            self.lbl_Fav.setPixmap(QPixmap(":/fav_empty.png"))
            app.processEvents()

    def checkInternet(self):
        """
        Ping www.google.com, if everything goes well, nothing will happen, otherwise a popup window will be shown,
        informing the user that there is no Internet Connection.
        The user can try it again, or close the application
        :return: --
        """


        status_ok, results = systemtest()
        if not status_ok:
            logger.warning("Some Network connections not available")
            # result.update({"internet" : service_internet})
            # result.update({"radiode" : service_radiode})
            # result.update({"lastfm" : service_lastfm})
            # result.update({"weathercom" : service_weathercom})
            self.broken_connections = []
            for key, value in results.iteritems():
                if not value:
                    self.broken_connections.append(key)

            if "internet" in self.broken_connections:

                ret = self.askQuestion(self.tr("Can not establish an online-connection"),
                                       self.tr("Try again"),
                                 self.tr("Radio, Weatherforecast as well as onlinefuncitons will get deactivated."),
                                 self.tr("Ok, de-activate"))
                if ret == 0:  # 0 ist "Erneut prüfen
                    logger.warning("Re-Check")
                    self.checkInternet()
                else:
                    logger.info("User want to deactivate radio module and weather because of no network connection")
                    #self.shutdowntrigger = True
                    #self.close()
                    logger.warning("deactivating radio Tab")
                    #self.tabWidget_main.removeTab(0)
                    self.tabWidget_main.setTabEnabled(0, False)
                    #self.tabWidget_mainPage1.setEnabled(False)
                    logger.warning("deactivating weather Tab")
                    #self.tabWidget_main.removeTab(1)
                    self.tabWidget_main.setTabEnabled(2, False)
                    self.tabWidget_main.setCurrentIndex(1)

            else:
                logger.warning("only some of the services will be de-activated")
                # "radiode" "lastfm" "weathercom"
                if "radiode" in self.broken_connections:
                    logger.info("deactivating searching function in radio")
                if "lastfm" in self.broken_connections:
                    logger.info("I just can not download albumart ... do nothing")

                if "weathercom" in self.broken_connections:
                    logger.info("I can not fetch weather informations .. deactivating weather Tab")
                    self.tab.setEnabled(False)

        else:
            logger.info("Network Connection etablished, all services available")

    def stackedWidgetOnePageBack(self):
        """
        If back button is clicked ...
        :return:
        """

        currentIndexTemp = self.stackedWidget.currentIndex()
        if currentIndexTemp is not 0:
            if currentIndexTemp == 3 or currentIndexTemp == 4 or currentIndexTemp == 7:
                self.stackedWidget.setCurrentIndex(1)
            elif (currentIndexTemp == 6) and (self.lW_kategorievorschlaege.count() == 0):
                self.stackedWidget.setCurrentIndex(1)
            else:
                self.stackedWidget.setCurrentIndex(self.stackedWidget.currentIndex()-1)
            self.currentIndex = self.stackedWidget.currentIndex()
            self.lastIndex = currentIndexTemp
            #print("Back")
        else:
            logger.debug("Button Zurueck should be invisible now !! why it is not ??")

    def checkHeaders(self):
        """
        Manage the headers of each widget and of each tab ...
        :return:
        """

        firstIndex = self.tabWidget_main.currentIndex()
        if firstIndex == 0:
            secondIndex = self.stackedWidget.currentIndex()
        elif firstIndex == 1:
            secondIndex = self.stackedWidget_2.currentIndex()
        elif firstIndex == 2:
            secondIndex = 0
        elif firstIndex == 3:
            secondIndex = 0
        elif firstIndex == 4:
            secondIndex = self.stackedWidget_3.currentIndex()

        headers={0 : {             # radio
                                   0: self.tr("Web Radio Tuner"),
                                   1: self.tr("Searching for..."),
                                   2: self.tr("Results for 'near of you':"),
                                   3: self.tr("Station-Proposals for you:"),
                                   4: self.tr("Searching for Category:"),
                                   5: None,                          # cat search will be handeled by its function
                                   6: self.tr("Favourites"),
                                   7: self.tr("Enter your keyword:")
                 },
                 1 : {             # media
                                   0: self.tr("Add Title"),
                                   1: self.tr("Media Player"),
                                   2: self.tr("Playlisteditor"),
                                   3: self.tr("Searchresults:"),
                                   4: self.tr("Enter your keyword:")

                 },
                 2 : {             # weather
                                   0: self.tr("Weatherforecast")

                 },
                 3 : {             # sleep Timer
                                   0: self.tr("Sleep-Timer")
                 },
                 4 : {             # Settings
                                   0: self.tr("Settings")
                 }
                }
        try:
            if headers[firstIndex][secondIndex] is not None:
                self.lbl_Ueberschrift.setText(headers[firstIndex][secondIndex])
        except KeyError:
            logger.error("No Header defined for tabindex{0}".format(self.tabWidget_main))
        #print(headers[firstIndex][secondIndex])

    def checkVisible(self):
        """
        Check if the return button have to be displayed
        :return:
        """
        newIndex = self.stackedWidget.currentIndex()

        if newIndex != 0:
            self.pBZurueck.setVisible(True)
        else:
            self.pBZurueck.setVisible(False)

        self.lastIndex = self.currentIndex
        self.currentIndex = newIndex

    def setNewDesign(self, index):                                                 # self.cB_design.currentIndexChanged
        '''
        This function is called by "currentIndexChanged" of self.cB_design if the user changed the combobox - design
        1. Unloading the current resource, which is registered as "res"
        2. Loading new res
        3. Registering new res with reload(res) in sys.modules
        4. Load new Stylesheet from file
        5. Re-Setting all the icons to the different pushButtons
        Args:
            index: new index of self.cB_design
        Returns: Nothing
        '''

        global res
        newDesign = unicode(self.cB_design.itemText(index))
        if newDesign != "":
            logger.info("Setting new Design: {0}".format(newDesign))
            res.qCleanupResources() # the current resources are loaded under the name "res"
            if os.path.isfile(os.path.join(cwd, "res", "designs", newDesign, "res.py")):
                try:
                    res = importlib.import_module(".res", package="res.designs.{0}".format(newDesign))
                    global_vars.configuration.get("GENERAL").update({"design": newDesign})
                except ImportError:
                    logger.error("Error: Design can not be loaded!, Loading Fallback!")
                    try:
                        res = importlib.import_module(".res",
                                                      package="res.designs.fallback")
                    except ImportError:
                        logger.error("Fallback can not be loaded! Aborting.")
                        raise ImportError
                    else:
                        # assure that right stylesheet is loaded if the user-design has failed to load...
                        global_vars.configuration.get("GENERAL").update({"design": "fallback"})
            else:
                logger.error("Specified Design does not exist on this machine! Loading fallback")
                try:
                    res = importlib.import_module(".res",
                                                  package="res.designs.fallback")
                except ImportError:
                    logger.error("Fallback can not be loaded! Aborting.")
                else:
                    # assure that right stylesheet is loaded if the user-design has failed to load...
                    global_vars.configuration.get("GENERAL").update({"design": "fallback"})
            reload(res)  # register new module in sys.modules
            logger.info("Loading Stylesheet: {0}".format(os.path.join(cwd, "res", "designs", global_vars.configuration.get("GENERAL").get("design"),
                                       "stylesheet.qss")))
            try:
                with open(os.path.join(cwd, "res", "designs", global_vars.configuration.get("GENERAL").get("design"),
                                       "stylesheet.qss")) as style:
                    stylenew = style.read()
                self.setStyleSheet(stylenew)
            except:
                logger.error("Stylesheet can not be loaded! Aborting.")
                raise ImportError

            # updating all used icons.
            logger.info("Updating Icons")
            self.pBHome.setIcon(QIcon(":/home.png"))
            if self.mode == "media":
                self.pBSuchen.setIcon(QIcon(":/show_playlist.png"))
                self.pBZurueck.setIcon(QIcon(":/search.png"))
                self.pBFavoriten.setIcon(QIcon(":/search_folder.png"))
            else: # mode == "radio"
                self.pBSuchen.setIcon(QIcon(":/search.png"))
                self.pBZurueck.setIcon(QIcon(":/back.png"))
                self.pBFavoriten.setIcon(QIcon(":/favorites.png"))
            self.tabWidget_main.setTabIcon(0, QIcon(":/radio.png"))
            self.tabWidget_main.setTabIcon(1, QIcon(":/media.png"))
            self.tabWidget_main.setTabIcon(2, QIcon(":/weather.png"))
            self.tabWidget_main.setTabIcon(3, QIcon(":/clock.png"))
            self.tabWidget_main.setTabIcon(4, QIcon(":/config.png"))
            self.pBVol_down.setIcon(QIcon(":/volume_down.png"))
            self.pBVol_up.setIcon(QIcon(":/volume_up.png"))
            self.pB_Audio_play_pause.setIcon(QIcon(":/play.png"))
            self.pB_Audio_stop.setIcon(QIcon(":/stop.png"))
            self.pB_Audio_back.setIcon(QIcon(":/backward.png"))
            self.pB_Audio_forward.setIcon(QIcon(":/next.png"))
            self.pB_Audio_play_pause_2.setIcon(QIcon(":/play.png"))
            self.pB_Audio_stop_2.setIcon(QIcon(":/stop.png"))
            self.pB_Audio_back_2.setIcon(QIcon(":/backward.png"))
            self.pB_Audio_forward_2.setIcon(QIcon(":/next.png"))
            self.pB_relead_tree.setIcon(QIcon(":/refresh.png"))
            self.pB_autorepeat.setIcon(QIcon(":/repeat.png"))
            self.pB_autorepeat_2.setIcon(QIcon(":/repeat.png"))
            self.pB_markAll.setIcon(QIcon(":/selectall.png"))
            self.pB_add_to_playlist.setIcon(QIcon(":/add.png"))
            self.pB_add_to_playlist_2.setIcon(QIcon(":/add.png"))
            self.pB_move_down_2.setIcon(QIcon(":/up.png"))
            self.pB_del_from_playlist.setIcon(QIcon(":/del.png"))
            self.pB_add_on_playlist.setIcon(QIcon(":/add.png"))
            self.pB_move_down.setIcon(QIcon(":/down.png"))

            #if everything was OK, update Value in current conf accordingly.
            write_conf(os.path.join(cwd, "webradio.conf"), "GENERAL", "design",
                       global_vars.configuration.get("GENERAL").get("design"), ".conf")

    def switchModeTo(self, from_mode, to_mode):
        """
        This function is called when the settings are loaded at startup, and when the tab-index is changed.
        :param from_mode:
        :param to_mode:
        :return:
        """
        if from_mode == "media" and to_mode != "media":      # when media-player is leaved.
            #save current playlist
            if self.player is not None:
                self.player.save_playlist("media_playlist")      # assure that current playlist is saved...
                logger.info("Saved playlist, media_playlist")

        if to_mode == "radio":
            if not self.audio_amp_isActive:
                self.emit(SIGNAL("sig_audio_amp_on"))
                self.emit(SIGNAL("sig_status_on"))

            logger.info("Switching to Radio-Mode")
            ################################################################################ Disconnect Media specific

            ################################################################################# Specific Connections
            self.connect(self.mpd_listener, SIGNAL("sig_mpd_songChanged"), self.on_currentTrackChanged)

            ##################################################################################  Button Connections
            try:
                self.pBZurueck.clicked.disconnect()
                self.pBSuchen.clicked.disconnect()
                self.pBHome.clicked.disconnect()
                self.pBFavoriten.clicked.disconnect()
                #self.disconnect(self.mpd_listener, SIGNAL("sig_mpd_timeElapsed_information"))
                #
                #self.connect(self.virtualKeyboard, SIGNAL("sigInputString"))

            except:
                print("can not disconnect media because they are not connected")
                pass


            self.pBZurueck.clicked.connect(self.stackedWidgetOnePageBack)
            self.pBSuchen.clicked.connect(self.onSuchen)
            self.pBHome.clicked.connect(self.onHome)
            self.pBFavoriten.clicked.connect(self.onFavoriten)
            #self.connect(self.virtualKeyboard, SIGNAL("sigInputString"), self.onCustomSearch_OK)
            self.stackedWidget.currentChanged.connect(self.checkVisible)

            ################################################################################## preset right Buttons

            self.pBHome.setIcon(QIcon(":/home.png"))
            self.pBSuchen.setIcon(QIcon(":/search.png"))
            self.pBZurueck.setIcon(QIcon(":/back.png"))
            self.pBFavoriten.setIcon(QIcon(":/favorites.png"))

            if not self.pBHome.isVisible():
                self.pBHome.setVisible(True)
                self.pBSuchen.setVisible(True)
                self.pBFavoriten.setVisible(True)

            self.checkVisible()

            self.mode = "radio"

            if from_mode == "media":
                #play last Radio station
                if not self.myCurrentStation:
                    self.playStationByID(self.playedLast)
                else:
                    id_to_play = self.myCurrentStation.id
                    self.myCurrentStation = None
                    self.playStationByID(id_to_play)
                    # load favorites will be done anyway in playStationByID
                if self.tabWidget_main.currentIndex() != 0:
                    self.tabWidget_main.setCurrentIndex(0)


        elif to_mode == "media":

            self.pBZurueck.setVisible(True)

            if not self.audio_amp_isActive:
                self.emit(SIGNAL("sig_audio_amp_on"))
                self.emit(SIGNAL("sig_status_on"))

            if from_mode == "media":

                if not self.pBHome.isVisible():
                    self.pBHome.setVisible(True)
                    self.pBSuchen.setVisible(True)
                    self.pBFavoriten.setVisible(True)
                    if self.pBHome.isVisible():

                        #print("Abort because you are comming just from weather widget")
                        return

            if self.player is None:
                self.player = MPC_Player()

            logger.info("Swithing from Radio to Media Mode")
            #load last media-playlist
            if self.player.load_playlist("media_playlist"):
                logger.info("Loading of media-playlist suceeded.")
            else:
                self.player.clear()

            logger.info("Switching to Media-Mode")
            try:
                self.pBZurueck.clicked.disconnect()
                self.pBSuchen.clicked.disconnect()
                self.pBHome.clicked.disconnect()
                self.pBFavoriten.clicked.disconnect()
                #self.disconnect(self.virtualKeyboard, SIGNAL("sigInputString"))
            except:
                logger.warning("can not disconnect radio because they are not connected")
                pass

            self.pBZurueck.clicked.connect(self.onCustomSearch_media)
            self.pBSuchen.clicked.connect(lambda : self.stackedWidget_2.setCurrentIndex(0))
            self.pBHome.clicked.connect(lambda : self.stackedWidget_2.setCurrentIndex(1))
            self.pBHome.clicked.connect(lambda: self.on_media_local_changed("HOME", "HOME", "", ""))
            self.pBFavoriten.clicked.connect(self.on_show_current_playlist)



            self.connect(self.mpd_listener, SIGNAL("sig_mpd_timeElapsed_information"), self.update_seek_slider)
            self.slide_seek.sliderPressed.connect(lambda : self.lockSeekSlider(True))
            self.slide_seek.sliderReleased.connect(lambda : self.lockSeekSlider(False))
            self.slide_seek.sliderMoved.connect(lambda : self.lockSeekSlider(None))


            self.pBHome.setIcon(QIcon(":/home.png"))
            self.pBSuchen.setIcon(QIcon(":/show_playlist.png"))
            self.pBZurueck.setIcon(QIcon(":/search.png"))
            self.pBFavoriten.setIcon(QIcon(":/search_folder.png"))

            if not self.pBHome.isVisible():
                self.pBHome.setVisible(True)
                self.pBSuchen.setVisible(True)
                self.pBFavoriten.setVisible(True)
                self.pBZurueck.setVisible(True)

            """
            #self.model = QDirModel(['*.mp3'], QDir.AllEntries|QDir.NoDotAndDotDot|QDir.AllDirs, QDir.Name)
            self.myProvider = FileIconProvider()
            self.model = LM_QFileSystemModel()
            self.model.setRootPath(MusicFolder)
            self.model.setIconProvider(self.myProvider)
            self.model.setFilter(QDir.AllEntries|QDir.NoDotAndDotDot|QDir.AllDirs|QDir.Name)
            self.model.setNameFilters(['*.mp3','*.MP3'])

            #self.model.setSorting(QDir.Name|QDir.DirsFirst)
            self.treeView.setModel(self.model)
            self.treeView.setRootIndex(self.model.index(MusicFolder))
            self.treeView.setIconSize(QSize(32,32))
            self.treeView.setAnimated(False)
            """
            self.exchange_model()

            self.pB_relead_tree.clicked.connect(self.exchange_model )
            for i in range(1,4):
                self.treeView.hideColumn(i)

            if not self.mpd_listener.isrunning():      # assure that listener is running ...
                self.mpd_listener.startNotifier()


            self.playlisteditor = Playlisteditor(self.listWidget, self.player)

            self.player.updateDatabase(VARIABLE_DATABASE)

            self.playlisteditor = Playlisteditor(self.listWidget, self.player, self)

            self.pB_move_down_2.clicked.connect(self.playlisteditor.moveItemUp)
            self.pB_move_down.clicked.connect(self.playlisteditor.moveItemDown)
            self.pB_del_from_playlist.clicked.connect(self.playlisteditor.deleteItem)
            self.pB_add_on_playlist.clicked.connect(lambda : self.stackedWidget_2.setCurrentIndex(0))
            self.connect(self.mpd_listener, SIGNAL("sig_mpd_media_local_changed"),
                         self.playlisteditor.grapCurrentPlaylist)
            self.connect(self.mpd_listener, SIGNAL("sig_mpd_playlist_changed"),
                         lambda : self.on_media_local_changed("HOME", "HOME", "", ""))
            self.model.directoryLoading.connect(lambda : self.splash_loading(True))
            self.model.directoryLoaded.connect(lambda : self.splash_loading(False))

            self.on_show_current_playlist()

            self.mode = "media"
            self.onAutoRepeat("1", True if self.player.status('repeat') == "1" else False)
            self.widget_Standby.setInitialState("on") #this do not emit anything, only setting the correct logo.
            self.widget_Mute.show_unmute()

        else:
            logger.error("Mode is not supported:", to_mode)

    @pyqtSlot(int) # Connected to tabWidget_main.currentChanged.
    def on_tabIndexChanged(self, newIndex):
        """

        :param newIndex: the new index if another tab was selected, trigger for "switch to mode"
        :return:
        """
        logger.info("TabIndex Changed to: {0}".format(newIndex))

        if newIndex == 0:
            to_mode = "radio"

        elif newIndex == 1:
            to_mode = "media"

        elif newIndex == 2:
            #weather
            if self.pBHome.isVisible():
                self.pBHome.setVisible(False)
                self.pBSuchen.setVisible(False)
                self.pBZurueck.setVisible(False)
                self.pBFavoriten.setVisible(False)

            self.weatherWidget.update_widget()
            return
        elif newIndex == 3:
            #sleep-timer
            if self.pBHome.isVisible():
                self.pBHome.setVisible(False)
                self.pBSuchen.setVisible(False)
                self.pBZurueck.setVisible(False)
                self.pBFavoriten.setVisible(False)
            return
        elif newIndex == 4:
            #settings
            if self.pBHome.isVisible():
                self.pBHome.setVisible(False)
                self.pBSuchen.setVisible(False)
                self.pBZurueck.setVisible(False)
                self.pBFavoriten.setVisible(False)
            return
        else:
            logger.critical("Index is out of Range or not handeled !")
            return
        logger.info("Swithing from {0} to {1}".format(self.mode, to_mode))
        self.switchModeTo(self.mode, to_mode)

######################################## Bindings to Buttons ########################################################

    @pyqtSlot()  # Connected to self.pBSuchen                                                                .clicked
    def onSuchen(self):
        """
        If button "onSuchen" was clicked, switch to stackedWidget Index 1 (site 2)
        """
        self.lbl_Ueberschrift.setText(self.tr("Searching for:"))
        self.stackedWidget.setCurrentIndex(1)

    @pyqtSlot()  # Connected to self.pBHome                                                                  .clicked
    def onHome(self):
        """
        If button "home" was clicked, switch so stackedWidget index 0 (site 1)
        """
        self.stackedWidget.setCurrentIndex(0)

    @pyqtSlot()  # Connected to self.pBFavoriten                                                             .clicked
    def onFavoriten(self):
        """
        if button favorites was clicked, construct favorites list in page 7 (index 6) from self.favorites (dict)
        with {id: <radiostation class>}.
        Switch to index 6 ofo stacked widget after populating the listWidget is done.
        """

        if self.lW_stationen_nach_cat.count() != 0:              # if the listWidget is not empty, because of previouse
            self.lW_stationen_nach_cat.clear()                   # ations, clear its contents.

        for key in self.favorites.iterkeys():                    # for every entry in favorites dict
            #print(key)                        # id              # extrakt "id"
            #print(self.favorites[key].name)   # name            # and "name" to display
            newItem = QListWidgetItem(self.lW_stationen_nach_cat)  # create new ListWidgetItem (parent= ListWidget)
            newItem.setText(self.favorites[key].name)              # the "text" which the Item should be named
            newItem.setData(Qt.UserRole, self.favorites[key].id)   # the "data" which should be carried by the item (id)
            newItem.setIcon(QIcon(":/fav.png"))                    # because it is a favorite, lets give it a "star"
        self.lW_stationen_nach_cat.sortItems(Qt.AscendingOrder)    # sort from A-Z for easier search if the list is
        self.stackedWidget.setCurrentIndex(6)                      # growing... than swith to the index and show it...

    @pyqtSlot()  # Connected to self.pB_in_ihrer_naehe                                                       .clicked
    def onInIhrerNaehe(self):
        """
        if button 'in Ihrer Nähe' was clicked, ask for radio-stations at www.radio.de
        returned is a dict. Extract necessary informations (id and name of station) and list it in a List Widget
        at Index 2
        """

        self.emit(SIGNAL("start_loading"))
        if self.lW_in_ihrer_naehe.count() is 0:                    # function is called only, if it is not called

            thread = WorkerThread(self.RadioDeAPI.get_local_stations,10)
            thread.start()
            while not thread.isFinished():
                app.processEvents()
            localStations = thread.result()
            #localStations = self.RadioDeAPI.get_local_stations(10) # earlier. The result dont change significantly...
                                                                   # if it is called the first time, get locals ...
            for dicts in localStations:                            # get every dict as a singel one
                app.processEvents()
                newItem = QListWidgetItem(self.lW_in_ihrer_naehe)  # create a new entry for every dict
                newItem.setText(dicts["name"])                     # give it a name (station name)
                newItem.setData(Qt.UserRole, dicts["id"])          # set the id from radio.de as its data
        self.lW_in_ihrer_naehe.sortItems(Qt.AscendingOrder)        # sort it from A-Z

        self.stackedWidget.setCurrentIndex(2)                      # switch to the correct index
        self.emit(SIGNAL("stop_loading"))

    @pyqtSlot()  # Connected to self.pB_Sendervorschlaege_fuer_sie                                           .clicked
    def onSendervorschlaege(self):
        """
        if button 'sendervorschläge' is clicked, request www.radio.de for station suggestions.
        do this only once (if ListWidget sendervorschlaege is empty) and populate it with ListwidgetItems

        """
        self.stackedWidget.setCurrentIndex(3)                        # switch to the correct index
        self.emit(SIGNAL("start_loading"))
        if self.lW_sendervorschlaege.count() is 0:                 # function is called only, if it is not called
            #localStations = self.RadioDeAPI.get_recommendation_stations() # earlier. The result dont change
            thread = WorkerThread(self.RadioDeAPI.get_top_stations)
            thread.start()
            while not thread.isFinished():
                app.processEvents()
            localStations = thread.result()
            #localStations = self.RadioDeAPI.get_top_stations()       # receive the top100 stations instead...
            #localStations = self.RadioDeAPI._get_most_wanted()      # receive the most wanted 25 stations(no function)
            for dicts in localStations: #["topBroadcasts"]: #used for mostwanted only  # get every dict as a singel one
                app.processEvents()
                newItem = QListWidgetItem(self.lW_sendervorschlaege) # create a new entry for every dict
                newItem.setText(dicts["name"])                       # give it a name (station name)
                newItem.setData(Qt.UserRole, dicts["id"])            # set the id from radio.de as its data
        self.lW_sendervorschlaege.sortItems(Qt.AscendingOrder)       # sort it from A-Z
        self.emit(SIGNAL("stop_loading"))
        #self.stackedWidget.setCurrentIndex(3)                        # switch to the correct index

    @pyqtSlot()  # Connected to pB_nach_Genre, pB_nach_Land, pB_nach_Stadt, pB_nach_Sprache,pB_nach_Thema    .clicked.
    def onCatSearch(self, category):
        """
        if button 'suche nach ******' is clicked, ask www.radio.de for the categories and display it at Index5.
        this will be done every time a category was clicked, no matter if it was already searched ....
        :param category: 'genre', 'topic', 'country', 'city', 'language',
        """
        self.tr('genre')
        self.tr('topic')
        self.tr('country')
        self.tr('city')
        self.tr('language')
        self.lbl_Ueberschrift.setText(self.tr("Searching for %1:").arg(self.tr(category)))
        self.emit(SIGNAL("start_loading"))
        self.stackedWidget.setCurrentIndex(5)                         # switch to the correct index
        if self.lW_kategorievorschlaege.count() != 0:        # if Listwidget is not empty...
            self.lW_kategorievorschlaege.clear()             # clear contents....
        thread = WorkerThread(self.RadioDeAPI.get_categories,category)
        thread.start()
        while not thread.isFinished():
            app.processEvents()
        possibleCategories = thread.result()
        #possibleCategories = self.RadioDeAPI.get_categories(category) # API request for category entry
        for cat in possibleCategories:                                # get every dict as a singel one
            app.processEvents()
            newItem = QListWidgetItem(self.lW_kategorievorschlaege)   # create a new entry for every dict
            newItem.setText(cat)                                      # category value
            newItem.setData(Qt.UserRole, category)                    # category type
        self.lW_kategorievorschlaege.sortItems(Qt.AscendingOrder)     # sort it from A-Z
        self.emit(SIGNAL("stop_loading"))

    @pyqtSlot()  # Connected to self.pB_sender_suchen                                                        .clicked.
    def onCustomSearch(self):
        """
        swithch to page 8 (index7) which brings up the onScreenKeyboard...
        the onScreenKeyboard is connected with SIGNAL("sigInputString"), self.onCustomSearch_OK
        the overloaded signal (with a string) is Empty if abbrechen was clicked ... and got a string if ok was clicked.
        """
        self.virtualKeyboard.clearContent()
        self.stackedWidget.setCurrentIndex(7)

    @pyqtSlot()
    def onCustomSearch_media(self):
        #print("Switch to keyboard")
        self.virtualKeyboard2.clearContent()
        self.stackedWidget_2.setCurrentIndex(4)

    @pyqtSlot()    #Connected to self.pBFavoriten                                                            .clicked.
    def on_show_current_playlist(self):
        """
        This function is called if the user presses the "favorites" btn. And also it is called initially, when the
        mode is switched to Media-mode.
        """
        self.playlisteditor.grapCurrentPlaylist()
        self.stackedWidget_2.setCurrentIndex(2)

    @pyqtSlot()    #Connected to self.pB_add_to_playlist                                                     .clicked.
    def add_from_tree(self):
        """
        This function addes the selected files or folders of the tree-view to the current playlist.
        :return: first ID of playlist added (not used yet)
        """

        if self.player is None:
                self.player = MPC_Player()
        self.emit(SIGNAL("start_loading"))
        selections = self.treeView.selectedIndexes()
        app.processEvents()
        thread = WorkerThread(self.add_selection_to_playlist, selections)
        thread.start()
        while not thread.isFinished():
            app.processEvents()
        result = thread.result()
        self.treeView.clearSelection()
        self.emit(SIGNAL("stop_loading"))
        return result

    @pyqtSlot()
    def add_from_search(self):
        #print("Add from search")

        if self.player is None:
                self.player = MPC_Player()
        self.emit(SIGNAL("start_loading"))
        selections = self.treeWidget_2.get_current_selection()
        app.processEvents()
        thread = WorkerThread(self.add_selection_to_playlist_from_search, selections)
        thread.start()
        while not thread.isFinished():
            app.processEvents()
        result = thread.result()
        self.treeWidget_2.clearSelection()
        self.emit(SIGNAL("stop_loading"))

        return result

    @pyqtSlot()    #Connected to Control Btns of Media-Player (play, stop, back, next)                       .clicked.
    def mediaPlayerControl(self, command, specific=False):
        """
        self.pB_Audio_play.clicked.connect(lambda : self.mediaPlayerControl     ("play"))
        self.pB_Audio_stop.clicked.connect(lambda : self.mediaPlayerControl     ("stop"))
        self.pB_Audio_back.clicked.connect(lambda : self.mediaPlayerControl     ("back"))
        self.pB_Audio_forward.clicked.connect(lambda : self.mediaPlayerControl  ("next"))
        :param command: play, stop, back, next,
        """
        if command == "play":

            if self.player is not None:
                if not specific:
                    self.player.play()
                else:
                    item = self.listWidget.selectedIndexes()[0] if len(self.listWidget.selectedIndexes()) > 0 else None
                    if item is not None:
                        ID_to_play, pos = item.data(Qt.UserRole).toStringList()
                        self.player.play_title_with_ID(ID_to_play)
                    else:
                        self.player.play()
                if not self.stackedWidget_2.currentIndex() == 1:
                    self.stackedWidget_2.setCurrentIndex(1)


        elif command == "stop":          # I do not use "stop" ... I simulate it using "pause" and scroll to 0 sec. .
            if self.player is not None:
                currentState = self.player.status("state")
                if not currentState == "pause":
                    self.player.pause()
                    pos = self.player.status("song")
                    self.player.client.seek(pos, "0")

        elif command == "back":
            if self.player is not None:
                currentState = self.player.status("state")
                self.player.previous()
                if currentState == "pause":  # if the player was paused, and a different track was selected,
                    self.player.pause()      # pause after choosing a different track to avoid that the player starts
                    pos = self.player.status("song")  # playing without any user interaction
                    self.player.client.seek(pos, "0") # seek to position 0,

        elif command == "next":
            if self.player is not None:
                currentState = self.player.status("state")
                self.player.next()
                if currentState == "pause":
                    self.player.pause()
                    pos = self.player.status("song")
                    self.player.client.seek(pos, "0")

        else:
            logger.warning("Command not known:".format(command))   # more commands can be added using elif here...

######################################## Bindings to ListWidgets and their Items #####################################

    @pyqtSlot(QObject)  # Connected to lW_in_ihrer_naehe, lW_sendervorschlaege,lW_stationen_nach_cat       .itemClicked
    def onItemClicked(self, _QListWidgetItem):
        """
        Takes a QListWidgetItem, extract the 'data' which is the ID of a Station at www.radio.de
        playes it and set the label-texts
        :param _QListWidgetItem: QListWidgetItem which was clicked in QListwidget Connected to....
        """
        #radio-station was selected
        #print("Setting Item Selected")
        _QListWidgetItem.setSelected(True)
        #print("Updating")
        self.lW_stationen_nach_cat.repaint()
        self.lW_kategorievorschlaege.repaint()
        self.lW_sendervorschlaege.repaint()
        self.lW_in_ihrer_naehe.repaint()
        #print("process Events")
        app.processEvents()
        selectedDict = _QListWidgetItem.data(Qt.UserRole)
        station_id, status = selectedDict.toInt()
        nowPlaying = self.playStationByID(station_id)

        if nowPlaying:
            self.stackedWidget.setCurrentIndex(0)
            self.lbl_Ueberschrift.setText(u"on AIR")
            self.label.setText(self.tr("now playing ..."))

    @pyqtSlot(QObject)  # Connected to self.lW_kategorievorschlaege                                        .itemClicked
    def onCatChosen(self, _QListWidgetItem):
        """
        Function is called if any item in stackedWidget Index 5 is clicked, this means a category is selected.
        Takes a QListWidgetItem, extract the 'data' which is the category to search for and also a category value
        these two arguments are used to request the API at www.radio.de for stations in this category....
        :param _QListWidgetItem: QListWidgetItem which was clicked in QListwidget Connected to....
        """
        app.processEvents()
        if self.lW_stationen_nach_cat.count() != 0:
            self.lW_stationen_nach_cat.clear()
        #im searching for radiostations with categorie
        category = _QListWidgetItem.data(Qt.UserRole)
        category_type = category.toString()
        category_value = _QListWidgetItem.text()
        #print("Type: %s" % category_type)
        #print("Value: %s" % category_value)
        app.processEvents()
        self.emit(SIGNAL("start_loading"))
        self.stackedWidget.setCurrentIndex(6)
        app.processEvents()
        thread = WorkerThread(self.RadioDeAPI.get_stations_by_category,unicode(category_type),unicode(category_value))
        thread.start()
        while not thread.isFinished():
            app.processEvents()
        radiostations = thread.result()
        #radiostations = self.RadioDeAPI.get_stations_by_category(unicode(category_type), unicode(category_value))
        for station in radiostations:
            app.processEvents()
            newItem = QListWidgetItem(self.lW_stationen_nach_cat)
            newItem.setText(station["name"])
            newItem.setData(Qt.UserRole, station["id"])
        self.stopPleaseWait = True
        self.lbl_Ueberschrift.setText(self.tr("%1 Results for %2").arg(len(radiostations)).arg(category_value))
        self.lW_stationen_nach_cat.sortItems(Qt.AscendingOrder)
        #self.stackedWidget.setCurrentIndex(6)
        self.emit(SIGNAL("stop_loading"))

######################################## Bindings to custom signals ##################################################

    @pyqtSlot(str)  # Connected to self.virtualKeyboard,                                       SIGNAL("sigInputString")
    def onCustomSearch_OK(self, QString):
        """
        the onScreenKeyboard is connected with SIGNAL("sigInputString"), self.onCustomSearch_OK
        the overloaded signal (with a string) is Empty if abbrechen was clicked ... and got a string if ok was clicked.
        :param QString: Searchstring supplied by onScreenKeyboard
        """
        print("START ON CUSTOM SEARCH OK")
        if QString == "":                           # if cancel was clicked ...
            self.stackedWidget.setCurrentIndex(1)   # return to page 2
            return                                  # stop here...

        if self.lW_stationen_nach_cat.count() != 0: # if searchstring is not empty, clear last Items if there are any
            self.lW_stationen_nach_cat.clear()
        self.emit(SIGNAL("start_loading"))
        thread = WorkerThread(self.RadioDeAPI.search_stations_by_string, unicode(QString))  # Request API using string
        thread.start()
        while not thread.isFinished():
            app.processEvents()
        searchresult = thread.result()
        if len(searchresult) > 0:                                                   # if there is at least one hit...
            for dicts in searchresult:                                              # populate Index6 with Items
                app.processEvents()
                newItem = QListWidgetItem(self.lW_stationen_nach_cat)
                newItem.setText(dicts["name"])
                newItem.setData(Qt.UserRole, dicts["id"])                           # data is the station id.
            self.lW_stationen_nach_cat.sortItems(Qt.AscendingOrder)                 # sort from A-Z
            self.emit(SIGNAL("stop_loading"))
            self.stackedWidget.setCurrentIndex(6)            # if someting in Index 6 is clicked, it will be forwarded
        else:                                                # to "onItemClicked" which is managing the playing
            self.emit(SIGNAL("stop_loading"))
            app.processEvents()
            logger.info("No Matches for searchstring: {0}".format(unicode(QString).encode("utf-8")))
            self.askQuestion(self.tr("'%1' did not give any searchresults").arg(unicode(QString)),
                             self.tr("Try another"),
                             self.tr("Try another search keyword"))
            return True
            #if there was not a single hit, the user gets informed about and can repeat his request ....

    @pyqtSlot(str)
    def onCustomSearch_media_OK(self, QString):
        #print("Customsearch for ", QString)

        if QString == "":                           # if cancel was clicked ...
            logger.info("Search is empty")
            self.stackedWidget_2.setCurrentIndex(2)   # return to page 3 (Playlisteditor)
            return                                  # stop here...


        if self.player is not None:
            self.treeWidget_2.set_service(self.player)
        else:
            self.player = MPC_Player()
            self.treeWidget_2.set_service(self.player)

        self.treeWidget_2.populateTree(QString)  # Request API using string
        #self.treeWidget_2.setVisible(True)

        if self.treeWidget_2.topLevelItemCount() > 0:

            self.stackedWidget_2.setCurrentIndex(3)            # if someting in Index 6 is clicked, it will be forwarded
        else:                                                # to "onItemClicked" which is managing the playing
            app.processEvents()
            logger.info("No Matches for searchstring: {0}".format(QString.toLocal8Bit()))
            self.askQuestion(self.tr("'%1' did not give any searchresults").arg(unicode(QString)),
                             self.tr("Try another"),
                             self.tr("Try another search keyword"))

    @pyqtSlot(str)  # Connected to self.mpd_listener,                                     SIGNAL("sig_mpd_songChanged")
    def on_currentTrackChanged(self,newTrack):
        """
        Function is called by the mpd_listener which works like a daemon. He is monitoring the mpd-client. if there
        is a change in the current played trackname, the signal SIGNAL("sig_mpd_songChanged") is emitted. This is
        a overloaded signal which carries the new Track Information as a string.
        the function sets this string as new text for the textlable which is showing the current played track.
        :param newTrack: string
        """
        if self.mode == "radio":
            self.lbl_Musiktitel.setText(newTrack.decode("utf-8"))
            #logger.info("Set '{0}' as text-Content of 'lbl_Musiktitel'".format(newTrack.decode("utf-8")))
        else: #if mode == 'media'
            pass # ignoring, because this will not be visible anyway. also "media" is handled by other signals and func

    @pyqtSlot(str, str)  # Connected to self.mpd_listener,                             SIGNAL("sig_mpd_stationChanged")
    def on_currentStationChanged(self, newStation, url):
        """
        Function is called by the mpd_listener which works like a daemon. He is monitoring the mpd-client. if there
        is a change in the current played stationname, the signal SIGNAL("sig_mpd_stationChanged") is emitted. This is
        a overloaded signal which carries the new Station-Name Information as a string.
        the function sets this string as new text for the textlable which is showing the current played track.
        :param newStation: string
        """
        logger.info("Station Changed to {0}, with new URL {1}".format(newStation,url))
        #print("called on current station changed...", newStation, url)

        if newStation != "" and self.mode == "radio":                  # if the new station has a Name
            self.lbl_Sendername.setText(newStation.decode("utf-8"))    # display it
            self.label.setText(self.tr("now playing ..."))

        radioID=""
        trigger_for_switching_to_radio = False
        if url != "":                                                  # if there is an url sent
            #print("Evaluating:", url)
            if url.startswith("http://"):                              # check if the url is a url or a filename
                logger.debug("Received changed Station, but without name...")
                #print("received no station name but a url which starts with http://")
                if not self.mode == "radio":
                    #print("I am not in radio mode ... lets switch to it my changing tabIndex")
                    media_playlist = self.player.get_playlistWithId()
                    lastEntry = media_playlist[len(media_playlist)-1]
                    #print("lastEntry:", lastEntry)
                    #print("Delete ID:", lastEntry["id"])
                    self.player.client.deleteid(lastEntry["id"])
                    #print("switch to Index 0")
                    trigger_for_switching_to_radio = True

                for key in self.favorites.iterkeys():                      # check for each entry in the favorites dict
                    #print(self.favorites)
                    if self.favorites[key].url in url:                     # if the urls are matching
                        radioID = self.favorites[key].id                   # if yes, remember the ID of this station
                        print(radioID)
                        break                                              # and exit loop

                if not radioID == "" and not radioID == self.myCurrentStation.id:  # if the radioID is not emty any more
                    logger.info("Load new Logo, because Station changed")     # and it is not the same like the current
                    if not self.setStationLogoByID(radioID):
                        station = self.RadioDeAPI.get_station_by_station_id(radioID)   # station which is playing
                        LogoUrl = QString(station["pictureBaseURL"]+station["picture1Name"]) # get the station
                        self.setStationLogoByURL(LogoUrl, radioID)

                    self.myCurrentStation = self.favorites[radioID]

                    if self.myCurrentStation.isFavorite():
                        self.markAsFavorite(True)
                        logger.info("this is a Favorite {0}, {1}, {2}".format(self.myCurrentStation.name,
                                                                              self.myCurrentStation.id,
                                                                              self.myCurrentStation.fav))
                    else:
                        self.markAsFavorite(False)
                        logger.info("this is not a Favorite {0}, {1}, {2}".format(self.myCurrentStation.name,
                                                                                  self.myCurrentStation.id,
                                                                                  self.myCurrentStation.fav))
                if trigger_for_switching_to_radio:
                    self.tabWidget_main.setCurrentIndex(0)

            elif url.endswith((".mp3",".MP3")):
                logger.info("Received url which looks like a filename ({0}) .Ignoring it for changeStation".format(url))
                if self.mode is not "media":
                    print("Switch to media mode, because im in Radio Mode..")
                    self.tabWidget_main.setCurrentIndex(1)
                    #print("add track to playlist {0}".format(url))
                    ID_to_play = self.player.add(os.path.join(MusicFolder, url), MusicFolder)
                    #print("play ID: {0}".format(ID_to_play))
                    self.player.play_title_with_ID(ID_to_play)
                    self.stackedWidget_2.setCurrentIndex(1)
                    print("current self.mode is :", self.mode)

            else:
                logger.warning("Can not identify File-ending.. it also does not start with http...")

        else:
            logger.debug("Received changed Station, but without url...")

    @pyqtSlot(str)  # Connected to self.mpd_listener,                                   SIGNAL("sig_mpd_statusChanged")
    def on_statusChanged(self,newStatus):
        """
        Function is called by the mpd_listener which works like a daemon. He is monitoring the mpd-client. if there
        is a change in the current status, the signal SIGNAL("sig_mpd_statusChanged") is emitted. This is
        a overloaded signal which carries the new Status information as a string. The signal is only emitted if the
        previouse status was a different one.
        :param newStatus: string (play, stop, pause)
        """

        logger.info("Status Changed to: {0}".format(newStatus))
        if newStatus == "play":
            self.widget_Standby.setInitialState("on")
            self.widget_Mute.unmute()
        elif newStatus == "stop":
            if not self.player is None:
                if self.mode == "radio":
                    self.widget_Standby.standby_off()
        else:
            logger.warning("Pause... Not handled yet")

    @pyqtSlot()  # Connected to markAsFavorite(self, _bool=None):                       SIGNAL("sig_favorites_changed")
    def onFavoritesChanged(self):
        """
        This function is called, if the self.favorites list is changed in any way (favorite is deleted, or added)
        """
        logger.info("Favorites changed!")
        logger.info("Saving new Favorites")
        status, favlist = self.saveFavorites()                      # new favorite List is saved at HDD
        #print("Here is my favlist from 'saveFavorites'", favlist)
        if status and len(favlist) > 0:                             # if it was saved correctelly and it is greater
            logger.info("Writing Playlist")                               # than zero
            if self.writePlaylist(BasenameFavoritesPlaylist, favlist):    # a new playlist will be created
                logger.info("Updating MPD Playlist")
                self.playStationByID(self.myCurrentStation.id)  # and uploaded to mpd ( mainly for remote access)

    @pyqtSlot(int) # Connected to slider_vol.valueChanged, pBVol_down, pBVol_up       SIGNAL("clicked()"), valueChanged
    def on_volumeChanged(self, absoluteVol=None, relativeVol=None):
        """
        Function sets the value of mpd if player is existing, values are given by different clients
        CALLER:

        >> Mpd Daemon (Signal "sig_mpd_volumeChanged(int)") = absoluteVol
        >> slider (Signal "valueChanged(int)")              = absoluteVol
        >> pBVol_up / pBVol_down (lambda : +5 and -5)       = relativeVol
        :param absoluteVol: value between 0 and 100 if greater than 100 it will be limited to 100 (-1 = mute)
        :param relativeVol: vale positive or negative (+5 or -5) this is added to self.volume
        """
        #print("call volume Changed with", absoluteVol, relativeVol)
        if not absoluteVol is None:
            if not int(absoluteVol) < 0:
                if self.volume != int(absoluteVol):
                    #logger.info("Volume will be set to {0}".format(int(absoluteVol)))
                    #no need to write hundrets of volume-information lines to the logfile
                    self.volume = int(absoluteVol)

                    if self.player is not None:
                        try:
                            self.player.volume(level=self.volume)
                        except:
                            logger.critical("Can not set Volume to MPD! Problem with player!")
                            self.askQuestion(self.tr("A problem with MPD was detected!"), self.tr("Ok"),
                                             self.tr("Try to restart MPD, "
                                                     "or just reboot the system"))

                if self.slider_vol.value() != self.volume:
                    self.slider_vol.setValue(self.volume)
            else:
                logger.info("Mute (Vol is at -1) - "
                            "Only sliderposition was set to 0, self.volume = {0}".format(self.volume))
                self.slider_vol.setValue(0)

        if not relativeVol is None:
            newVolume = (self.volume + int(relativeVol)) if (self.volume + int(relativeVol)) <= 100 else 100
            if newVolume < 0:
                newVolume = 0
            if self.volume != newVolume:
                self.volume = newVolume
            else:
                return                  # if self.volume is at level of newValue anyway, dont set the playervol...
            if self.player is not None:
                try:
                    self.player.volume(level=newVolume)
                except:
                    logger.critical("Can not set Volume to MPD! Problem with player!")
                    self.askQuestion(self.tr("A problem with MPD was detected!"), self.tr("Ok"),
                                             self.tr("Try to restart MPD, "
                                                     "or just reboot the system"))
                #logger.info("Volume will be set to {0}".format(self.volume))
                #no need to write hundrets of volume-information lines to the logfile
                if self.slider_vol.value() != self.volume:
                    self.slider_vol.setValue(self.volume)

    @pyqtSlot(str, str, str, str) # Connected to mpd_listener                     SIGNAL("sig_mpd_media_local_changed")
    def on_media_local_changed(self, current_url, current_song, current_artist, current_album):
        """
        CALLER:

        self.mpd_listener, SIGNAL("sig_mpd_media_local_changed")
        self.pBHome.clicked.connect(lambda: ("HOME", "HOME", "", ""))
        self.mpd_listener, SIGNAL("sig_mpd_playlist_changed"),lambda : ("HOME", "HOME", "", ""))

        :param current_url: selfexplaining, when "HOME" only the lables and seekText will be updated (no artwork)
        :param current_song:selfexplaining, when "HOME" only the lables and seekText will be updated (no artwork)
        :param current_artist: if available, used for searching LastFM for the artwork of the album
        :param current_album: if available, used for searching LastFM for the artwork of the album
        :return:
        """

        if self.mode == "media":
            logger.info("Media Local Changed to:".format(current_url))
            #index = self.model.index("".join([MusicFolder,"/",current_url]))    # find the QModelIndex of file playing
            #self.treeView.clearSelection()
            #self.treeView.setCurrentIndex(index)                                 # select the file in QTreeView
            names = self.playlisteditor.tellMeWhatsPlaying()
            logger.info("Received PlaylistInformation (last,current,next)".format(names))
            self.lbl_previouse.setText(names[0])
            self.lbl_current_playing.setText(names[1])
            self.lbl_next.setText(names[2])
            self.lbl_current_seek.setText("")
            self.lbl_total_seek.setText("")
            self.slide_seek.setEnabled(False)
            self.onAutoRepeat("1", True if self.player.status('repeat') == "1" else False)

            if current_url == "HOME" and current_song == "HOME" and self.lbl_albumArt.pixmap():
                return

            if current_artist != "" and current_album != "":
                app.processEvents()
                logger.info("Searching for Albumart with {0} and {1}".format(current_album, current_artist))
                m = hashlib.md5()                            #create MD5 hash from given String
                m.update("{0}".format(current_album))
                extentions = ["jpg", "jpeg", "png"]
                possibleFiles = []
                for extention in extentions:
                    fileToCheck = os.path.join(AlbumArtFolder, "{0}.{1}".format(m.hexdigest(), extention))
                    possibleFiles.append(fileToCheck)
                DownloadTrigger = True
                for filename in possibleFiles:
                    if os.path.isfile(filename):
                        logger.info("File is existing at: {0}".format(filename))
                        albumart = QPixmap(filename)
                        self.lbl_albumArt.setPixmap(albumart.scaled(self.lbl_albumArt.width(),
                                                                    self.lbl_albumArt.height(),
                                                                    Qt.KeepAspectRatio, Qt.SmoothTransformation))
                        DownloadTrigger = False
                        return

                if DownloadTrigger:
                    logger.info("Try to download Link:")
                    try:
                        urlGrabber = LastFMDownloader(current_album, current_artist)
                        urlResult = urlGrabber.search_for_image()
                    except:
                        urlResult = None

                    logger.info("Searchresult: {0}".format(urlResult))
                    if urlResult is not None:
                        logger.info("Downloading url {0}".format(urlResult))
                        urlResult = str(urlResult)
                        if urlResult.endswith(".jpg"):
                            extention = "jpg"
                        elif urlResult.endswith(".jpeg"):
                            extention = "jpeg"
                        elif urlResult.endswith(".png"):
                            extention = "png"
                        else:
                            extention = "png"

                        fileToImport = os.path.join(AlbumArtFolder, "{0}.{1}".format(m.hexdigest(), extention))
                        url = str(urlResult)
                        urllib.urlretrieve(url, fileToImport)
                        if os.path.isfile(fileToImport):
                            albumart = QPixmap(fileToImport)
                            self.lbl_albumArt.setPixmap(albumart.scaled(self.lbl_albumArt.width(),
                                                                        self.lbl_albumArt.height(),
                                                                    Qt.KeepAspectRatio, Qt.SmoothTransformation))
                            return

            fallback = QPixmap(":/albumart_fallback.png")
            self.lbl_albumArt.setPixmap(fallback.scaled(self.lbl_albumArt.width(), self.lbl_albumArt.height(),
                                                                    Qt.KeepAspectRatio, Qt.SmoothTransformation))

    @pyqtSlot(str, str)  # Connected to mpd_listener,                         SIGNAL("sig_mpd_timeElapsed_information")
    def update_seek_slider(self, current, total):
        """
        This function updates the seek-slider to the current position while playing a track, it is called nearly all
        0,5 seconds by the signal timeElapsed_information from the mpd_listener.
        :param current: current time played in absolute seconds
        :param total: total time of the track-length in absolute seconds

        Setting minimum and maximum of the slider,
        setting current value,
        setting the text, of the lables which are in front and behind the seek-slider
        """
        if not self.blockSeekSlider:   # if the slider is currently not moved by the user ...
            self.slide_seek.setEnabled(True)
            self.slide_seek.setMinimum(0)
            self.slide_seek.setMaximum(int(total))
            self.slide_seek.setValue(int(current))
            self.lbl_current_seek.setText("{0}".format(time.strftime('%M:%S', time.gmtime(int(current)))))
            self.lbl_total_seek.setText("{0}".format(time.strftime('%M:%S', time.gmtime(int(total)))))

    @pyqtSlot()  # Connected to usb_manager                                              SIGNAL("sig_usb_disconnected")
    def on_usb_disconnected(self):
        self.gpio_watchdog.set_output_LOW(32)      # turn off status LED
        logger.info("Webradio: USB Stick disconnected")
        if self.mode == "media":
            self.exchange_model()
            pass

    @pyqtSlot()  # Connected to usb_manager                                                 SIGNAL("sig_usb_connected")
    def on_usb_connected(self):
        self.gpio_watchdog.set_output_HIGH(32)      # turn on status LED
        logger.info("Webradio: USB Stick connected")
        if self.mode == "media":
            self.exchange_model()
        if self.player is not None:
            self.player.updateDatabase(VARIABLE_DATABASE)

    @pyqtSlot()  # Connected to signal                                                      SIGNAL("sig_audio_amp_on")
    def on_audio_amp_on(self):
        """
        Switch on audio amplifier using relais 1 & 2  (pin 31 and 33)
        """
        self.gpio_watchdog.set_output_HIGH(31)
        self.gpio_watchdog.set_output_HIGH(33)
        self.audio_amp_isActive = True

    @pyqtSlot()  # Connected to signal                                                      SIGNAL("sig_audio_amp_off")
    def on_audio_amp_off(self):
        """
        Switch off audio amplifier using relais 1 & 2  (pin 31 and 33)
        """
        self.gpio_watchdog.set_output_LOW(31)
        self.gpio_watchdog.set_output_LOW(33)
        self.audio_amp_isActive = False

    @pyqtSlot()  # Connected to                                                             SIGNAL("sig_status_on")
    def statusLED_on(self):
        self.gpio_watchdog.set_output_HIGH(36)      # turn on status LED

    @pyqtSlot()  # Connected to                                                             SIGNAL("sig_status_off")
    def statusLED_off(self):
        self.gpio_watchdog.set_output_LOW(36)      # turn on status LED

    @pyqtSlot()  # Connected to                                                             SIGNAL("sig_LCD_on")
    def LCD_on(self):
        self.gpio_watchdog.set_output_LOW(35)      # turn LCD ON

    @pyqtSlot()  # Connected to                                                             SIGNAL("sig_LCD_off")
    def LCD_off(self):
        self.gpio_watchdog.set_output_HIGH(35)      # turn LCD OFF

    @pyqtSlot()
    def onSelectAll(self):

        if len(self.listWidget.selectedIndexes()) > 1:
            self.listWidget.clearSelection()
            self.listWidget.setSelectionMode(QAbstractItemView.SingleSelection)
            return
        self.listWidget.setSelectionMode(QAbstractItemView.MultiSelection)
        self.listWidget.selectAll()

    @pyqtSlot()
    def onAutoRepeat(self, ident, forceState=None):
        if forceState is not None:
            self.pB_autorepeat.setChecked(forceState)
            self.pB_autorepeat_2.setChecked(forceState)
            if self.pB_autorepeat.isChecked():
                self.pB_autorepeat.setIcon(QIcon(":/repeat_active.png"))
                #self.pB_autorepeat.setIconSize(self.pB_autorepeat.sizeHint()*2)
                self.pB_autorepeat_2.setIcon(QIcon(":/repeat_active.png"))
                #self.pB_autorepeat_2.setIconSize(self.pB_autorepeat_2.sizeHint()*2)
            else:
                self.pB_autorepeat.setIcon(QIcon(":/repeat.png"))
                #self.pB_autorepeat.setIconSize(self.pB_autorepeat.sizeHint()*2)
                self.pB_autorepeat_2.setIcon(QIcon(":/repeat.png"))
                #self.pB_autorepeat_2.setIconSize(self.pB_autorepeat_2.sizeHint()*2)
            return

        if ident == "1":
            newStatus = self.pB_autorepeat.isChecked()
            # if newStatus == True >> anderes Symbol
        else:
            newStatus = self.pB_autorepeat_2.isChecked()
            # if newStatus == True >> anderes Symbol

        self.player.setRepeat(newStatus)

        if ident == "1":
            self.pB_autorepeat_2.setChecked(newStatus)
            # if newStatus == True >> anderes Symbol
        else:
            self.pB_autorepeat.setChecked(newStatus)
            # if newStatus == True >> anderes Symbol

        if self.pB_autorepeat.isChecked():
            self.pB_autorepeat.setIcon(QIcon(":/repeat_active.png"))
            #self.pB_autorepeat.setIconSize(self.pB_autorepeat.sizeHint()*2)
            self.pB_autorepeat_2.setIcon(QIcon(":/repeat_active.png"))
            #self.pB_autorepeat_2.setIconSize(self.pB_autorepeat_2.sizeHint()*2)
        else:
            self.pB_autorepeat.setIcon(QIcon(":/repeat.png"))
            #self.pB_autorepeat.setIconSize(self.pB_autorepeat.sizeHint()*2)
            self.pB_autorepeat_2.setIcon(QIcon(":/repeat.png"))
            #self.pB_autorepeat_2.setIconSize(self.pB_autorepeat_2.sizeHint()*2)

    @pyqtSlot()   # Connected to                                                           SIGNAL("onSleepTimerElapsed")
    def onSleepTimerElapsed(self):
        '''
        Is called by the signal "sleeptimerelapsed" of the Sleep-Timers at Page4.
        If this timer gets fully ellapsed, the webradio will shutdown.
        '''
        self.close()
        if not args.debug:
            self.systemCall("sudo shutdown -h now")
        else:
            logger.debug(u"Would shutdown now!")

    @pyqtSlot()   # Connected to                                                   SIGNAL("onSleepTimerCloseToElapsed")
    def onSleepTimerCloseToElapsed(self):
        # start a DLG in a new Thread which dos not block the further execution of the sleeptimer
        QTimer.singleShot(0, self.showShutdownDlg)

    def showShutdownDlg(self):  # called by a Singleshot-Timer started with "onSleepTimerCloseToElapsed"

        dialog = ShutdownDialog(text=self.tr("Your Webradio will shutdown now!"), options=[self.tr("Abort!"),
                                                                                           self.tr("Continue...")],
                                parent=self)
        dialog.exec_()
        if dialog.exitStatus is None:
            return False
        elif dialog.exitStatus == self.tr("Abort!"):
            self.widget_sleep_timer.stop(silent=False)


    ##################################################  GPIO Handling ##################################################

    @pyqtSlot(str)  # Connected to gpio_watchdog,                                          SIGNAL("gpio_rotary_turned")
    def signalreader_rotary(self, direction):
        if direction == "clockwise":
            #print("Clockwise")
            self.on_volumeChanged(relativeVol="+1")
        if direction == "anticlockwise":
            #print("Anti-Clockwise")
            self.on_volumeChanged(relativeVol="-1")

    @pyqtSlot(str)  # Connected to gpio_watchdog,                                         SIGNAL('gpio_button_pressed')
    def signalreader_buttons_on(self, channel):
        logger.info("Received button pressed signal: {0}".format(channel))

        if self.button_pressed != channel:
            self.button_pressed = channel
            self.long_press_timer = QTimer()
            self.long_press_timer.timeout.connect(lambda : self.long_press(channel))
            logger.info("Starting LongpressTimer")
            self.long_press_timer.start(2000) # after 2 seconds, it is a LONG Press
        else:
            logger.info("Ignore Event")

    @pyqtSlot(str)  # Connected to gpio_watchdog,                                        SIGNAL('gpio_button_released')
    def signalreader_buttons_off(self, channel):
        logger.info("Received button released signal: {0}".format(channel))
        if self.long_press_timer is not None:
            self.long_press_timer.stop()
            self.long_press_timer = None

        if not self.button_pressed is None:
            logger.info("User clicked button {0}".format(channel))
            if channel in self.gpio_presets:
                StationID = self.gpio_presets[channel]
                if self.mode != "radio":
                    self.switchModeTo(self.mode, "radio")

                self.playStationByID(StationID)
            elif int(channel) == 5:
                logger.info("Power/Eject Button was clicked, you want to eject the USB-Drive")
                #if self.player is not None:
                #if True:
                    #print("check mode")
                if self.mode == "media":
                    #print("media")
                    if self.player.status("state") == "playing":
                        if str(self.player.get_current_playing_filename()).startswith(VARIABLE_DATABASE):
                            # if something from the variable device with is about to be ejected is currently played.
                            logger.info("stop Player")
                            self.player.stop()
                    logger.info("remove all starting with: {0}".format(VARIABLE_DATABASE))
                    self.player.removeAllPlaylistEntrysStartingWithFilePath(VARIABLE_DATABASE)

                    if self.usb_manager.ismounted():
                        print("Webradio: umount usb stick ")
                        self.usb_manager.umount()
                    logger.info("update database")
                    self.player.updateDatabase(VARIABLE_DATABASE)

                elif self.usb_manager.ismounted():
                    logger.info("Webradio: umount usb stick ")
                    self.usb_manager.umount()

        self.button_pressed = None

    @pyqtSlot(str) # called from signalreader_button_on                         after 2 seconds pressed if not released
    def long_press(self, channel):
        self.long_press_timer.stop()
        self.long_press_timer = None
        self.button_pressed = None
        logger.info("Button {0} was long-pressed".format(channel))
        if int(channel) == 5:
            logger.info("Power/Eject Button was long pressed. Shutdown")
            self.shutdowntrigger = True
            self.close()
            return
        elif self.mode == "radio":
            StationID = self.myCurrentStation.id
            self.gpio_presets.update({channel : StationID})
            self.playStationByID(StationID)

    def signalreader_temp(self, temp, hum):
        """
        Is called by the GPIO watchdog, if a temp-sensor is connected, and temperature and humidity data can be read

        :param temp:
        :param hum:
        :return:
        """
        if GPIO_active:
            self.label_2.setText(u"{0:0.0f}°C {1:0.0f}% r.H.".format(int(temp), int(hum)))
        else:
            self.label_2.setText(self.tr("Outside: ")+"{0:0.0f}".format(int(self.weatherWidget.lbl_cur_temp.text()))+ \
                                 QChar(0xb0)+"C")

    ###################################################################################################################

    def lockSeekSlider(self, state):
        """
        CALLERS:

        Slider (seek) when pressed, released and moved.
        :param state: True, False, None (True, if the slider is clicked, false if the slider is released, none if
         the slider is moved (currently moving)
        :return: switches the state of self.blockSeekSlider (true, if values shoulb be ignored, false if values should
        be updated, because choosing the right position is finished by user
        """
        if state == True:
            self.blockSeekSlider = True
        elif state == False:
            timeToSeek = self.slide_seek.value()
            #print("seek to position", timeToSeek)
            pos = self.player.status("song")
            self.player.client.seek(pos, timeToSeek)
            self.blockSeekSlider = False
        elif state == None:
            self.lbl_current_seek.setText("{0}".format(time.strftime('%M:%S', time.gmtime(self.slide_seek.value()))))

    def playStationByID(self,station_id):
        """
        CALLER:

        >>readSettings             (startup_actions),
        >>unmute                   if self.player is None, (this is the case after it was muted...)
        >>update_mpd_playlist      because stream have to be stopped due to playlist update
        >>onItemClicked            if an Item was clicked in lW_in_ihrer_naehe, sendervorschlaege,stationen_nach_cat

        :param station_id: ID of radio-station from www.radio.de
        :return: starts playing using funktion "unmute"
        """
        logger.info("Called 'playStationByID' with {0}".format(station_id))

        if not self.mpd_listener.isrunning():
            self.mpd_listener.startNotifier()

        if self.myCurrentStation != None:
            if not self.myCurrentStation:
                self.myCurrentStation = None

            elif self.myCurrentStation.id == station_id:
                logger.info("Just continuing playing the current station")
                if self.player is None:
                    try:
                        logger.info("Player is none, will create a new one...")
                        self.player = MPC_Player(self.myCurrentStation.url)
                    except:
                        logger.critical("Can not create MPD-Player instance! Inform user")
                        self.askQuestion(self.tr("A problem with MPD was detected!"), self.tr("Ok"),
                                             self.tr("Try to restart MPD, "
                                                     "or just reboot the system"))
                else:
                    #if player is already existing an may be playing, this will stop it for a few seconds and start
                    #playing again, this is used to store favorites, store gpio presets... as a kind of feedback

                    self.player.stop()
                    self.player.clear()
                    self.player = None
                    try:
                        logger.info("Player is none, will create a new one...")
                        self.player = MPC_Player(self.myCurrentStation.url)
                    except:
                        logger.critical("Can not create MPD-Player instance! Inform user")
                        self.askQuestion(self.tr("A problem with MPD was detected!"), self.tr("Ok"),
                                             self.tr("Try to restart MPD, "
                                                     "or just reboot the system"))


                self.widget_Mute.unmute()           # this emitts (SIGNAL("sig_unmute")) connected to self.unmute()
                self.lbl_Sendername.setText(self.myCurrentStation.name) # setting station Name initially
                self.widget_Standby.setInitialState("on") #this do not emit anything, only setting the correct logo.
                return
            else:
                logger.info("Setting Current Station to None, because id is different from the one which is playing now.")
                self.myCurrentStation = None


        if station_id in self.favorites:          # if called station is already stored as favorite
            logger.info("ID is stored in favorites, taking link from stored files")
            self.myCurrentStation = self.favorites[station_id]     # load RadioStationObject from favorites
            self.myCurrentStation.setAsFavorite()                  # mark it to be a favorite
        else:                                     # if the called station is not already stored in favorites...
            self.emit(SIGNAL("start_loading"))
            logger.info("ID is NOT stored in favorites, Downloading details from radio.de")
            thread = WorkerThread(self.RadioDeAPI.get_station_by_station_id,station_id)
            thread.start()
            while not thread.isFinished():
                app.processEvents()
            station = thread.result()
            #station = self.RadioDeAPI.get_station_by_station_id(station_id)   # try to reach radio.de and request info
            self.emit(SIGNAL("stop_loading"))
            app.processEvents()

            if station is not False:                                          # if station-info was loaded sucessfully
                logger.info("Station detected, now constructing RadioStation Objekt")
                #print("Download sucessful, generating RadioStation-Object")
                #print(station)
                """
                {u'picture6Name': u't44.png',
                 u'family': [],
                 u'rating': 4.668634064080944,
                 u'topics': [],
                 u'rank': 31,
                 u'advertiser': [u'revshare'],
                 u'streamContentFormat': u'MP3',
                 u'picture1Name': u't100.png',
                 u'shortDescription': u'Das Internetradio HouseTime.FM \xfcberzeugt alle Liebhaber von House und Dance Sounds mit den besten der House Charts.',
                 u'id': 3179,
                 u'picture6TransName': u't44.png',
                 u'picture5TransName': u'',
                 u'city': u'',
                 u'genres': [u'Dance', u'House'],
                 u'picture4TransName': u't175.png',
                 u'recentTitles': [u'HouseTime.FM - HouseTime.FM - 24h House, Electro and More'],
                 u'subdomain': u'housetimefm',
                 u'picture5Name': u'',
                 u'streamURL': u'http://listen.housetime.fm/dsl.pls',
                 u'description': u'Das Internetradio HouseTime.FM \xfcberzeugt alle Liebhaber von House und Dance Sounds mit den besten der House Charts.',
                 u'currentTrack': u'HouseTime.FM - HouseTime.FM - 24h House, Electro and More',
                 u'link': u'http://www.housetime.fm/',
                 u'streamUrls': [{u'metaDataUrl': u'http://listen.housetime.fm/tunein-mp3-pls',
                                  u'streamUrl': u'http://listen.housetime.fm/tunein-mp3-pls',
                                  u'metaDataType': u'',
                                  u'contentType': u'audio/mpeg',
                                  u'loadbalanced': False,
                                  u'bitRate': 192,
                                  u'streamStatus': u'VALID',
                                  u'playingMode': u'STEREO',
                                  u'streamFormat': u'ICECAST',
                                  u'streamContentFormat': u'MP3',
                                  u'metaDataAvailable': False,
                                  u'sampleRate': 44100,
                                  u'type': u'STREAM',
                                  u'id': 7607861,
                                  u'idBroadcast': 3179},
                                 {u'metaDataUrl': u'http://ht.mp3.stream.tb-group.fm',
                                  u'streamUrl': u'http://ht.mp3.stream.tb-group.fm',
                                  u'metaDataType': u'',
                                  u'contentType': u'audio/mpeg',
                                  u'loadbalanced': False,
                                  u'bitRate': 192,
                                  u'streamStatus': u'VALID',
                                  u'playingMode': u'STEREO',
                                  u'streamFormat': u'ICECAST',
                                  u'streamContentFormat': u'MP3',
                                  u'metaDataAvailable': False,
                                  u'sampleRate': 44100,
                                  u'type': u'STREAM',
                                  u'id': 18287,
                                  u'idBroadcast': 3179}],
                 u'adParams': {u'genres': [u'Dance', u'House'], u'family': [], u'topics': [],
                               u'st_country': [u'Deutschland'], u'domain': [u'radio.de'],
                               u'languages': [u'Deutsch'], u'station': [u'housetimefm'], u'st_city': [],
                               u'type': [u'radio_station'], u'st_region': [u'Nordrhein-Westfalen'],
                               u'st_cont': [u'Europa']}, u'podcastUrls': [], u'picture1TransName': u't100.png',
                 u'bitrate': 192, u'picture4Name': u't175.png', u'name': u'HouseTime.FM', u'language': [u'Deutsch'],
                 u'oneGenre': u'Dance', u'picture2Name': u'', u'picture3Name': u'',
                 u'pictureBaseURL': u'http://static.radio.de/images/broadcasts/91/37/3179/',
                 u'country': u'Deutschland', u'playable': u'FREE', u'broadcastType': 1}
                """
                urltoparse = station["streamUrls"][0]["streamUrl"]
                if urltoparse.endswith("pls") and (len(station["streamUrls"]) > 1):
                    #print("take another url.. because first is a pls file")
                    for entry in station["streamUrls"]:
                        if not entry["streamUrl"].endswith("pls"):
                            urltoparse = entry["streamUrl"]

                self.myCurrentStation = RadioStation(name=station["name"],
                                                     station_id=station_id,
                                                     url=self.RadioDeAPI.parse_playlist(urltoparse),
                                                     fav=True if station_id in self.favorites else False)
            else:
                logger.warning("Can not reach radio.de, also the called station is not stored as favorite... Aborting")
                return False


        if self.myCurrentStation.isFavorite():
            self.markAsFavorite(True)
        else:
            self.markAsFavorite(False)

        if self.player is not None:
            logger.warning("Player is not None, stop, clear set to None, reload favorites")
            self.player.stop()
            self.player.clear()
            self.player = None

        if not self.setStationLogoByID(station_id):   # at first, check if station logo is already downloaded and can
            try:                                      # be set only with his ID of not, check if "station" is existing
                LogoUrl = QString(station["pictureBaseURL"]+station["picture1Name"])
                logger.info("Logo is not stored locally, downloading")
                self.setStationLogoByURL(LogoUrl, station_id)
            except:
                logger.info("Station Logo does not exist an cant be downloaded, setting Fallback")


        #self.player = GStreamerPlayer(self.RadioDeAPI.parse_playlist(station["streamUrls"][0]["streamUrl"]))
        logger.info("Creating new PLayer for: {0}".format(self.myCurrentStation.url))
        #try:
        self.player = MPC_Player(self.myCurrentStation.url)
        #except:
        #    logger.critical("Can not create MPD-Player instance! Inform user")
        #    self.askQuestion("Ein Problem mit MPD wurde entdeckt!", "Ok",
        #                                     "Versuchen Sie MPD neu zu starten, oder einen Reboot durch zu führen")

        logger.info("unmute now")
        self.widget_Mute.unmute()                      # this emitts (SIGNAL("sig_unmute")) connected to self.unmute()
        self.lbl_Sendername.setText(self.myCurrentStation.name) # setting station Name initially
                                                       # mpd-daemon running in background and updating lables.
        self.widget_Standby.setInitialState("on")  # this do not emit anything, only setting the correct logo.

        return True

    def setStationLogoByURL(self, LogoUrl, stationID):
        """
        This function downloads and sets the Logo for a radio-station by using its Logo-URL and stationID (this is used
        for the name, under which the logo-file is stored.

        :param LogoUrl: "http://www.the-url-for-the-logo/logo.png
        :param stationID: 6415
        :return: True or False
        """

        if LogoUrl.endsWith(".jpg"):
            extention = "jpg"
        elif LogoUrl.endsWith(".jpeg"):
            extention = "jpeg"
        elif LogoUrl.endsWith(".png"):
            extention = "png"
        else:
            #lets try it with an png
            extention = "png"

        fileToImport = os.path.join(LogoFolder, "{0}.{1}".format(stationID, extention))
        fallback = os.path.join(LogoFolder, "fallback.png")

        if os.path.isfile(fileToImport):
            self.lbl_Senderlogo.setPixmap(QPixmap(fileToImport).scaled(self.lbl_Senderlogo.width(),
                                                                       self.lbl_Senderlogo.height(),
                                                                       Qt.KeepAspectRatio, Qt.SmoothTransformation))
            return True

        else:
            downloadloop = True
            i = 0
            while (downloadloop is True):
                try:
                    urllib.urlretrieve(str(LogoUrl), filename=fileToImport)
                except: # IOError, e:
                    logger.error("Error downloading Logo: {0}".format(""))
                    return False

                if os.path.isfile(fileToImport):
                    self.lbl_Senderlogo.setPixmap(QPixmap(fileToImport).scaled(self.lbl_Senderlogo.width(),
                                                                       self.lbl_Senderlogo.height(),
                                                                       Qt.KeepAspectRatio, Qt.SmoothTransformation))
                    break
                else:
                    i += 1
                    logger.warning("Try to download Station Logo again. Loop No: {0}".format(i))
                    if i > 3:
                        logger.error("Unable to download Station Logo.... damn")
                        logger.error("No file '{0}' found for Logo ".format(fileToImport))
                        if os.path.isfile(fallback):
                            logger.info("Setting Fallbacklogo: {0}".format(fallback))
                            self.lbl_Sendername.setPixmap(QPixmap(fallback).scaled(self.lbl_Senderlogo.width(),
                                                                       self.lbl_Senderlogo.height(),
                                                                       Qt.KeepAspectRatio, Qt.SmoothTransformation))
                        else:
                            logger.error("No fallback-logo, named 'fallback.png' in '%s'" % LogoFolder)
                        break

            return True

    def setStationLogoByID(self, stationID):
        """
        This function can be used, if you dont know the station-picture-url ... in some cases you may only know the ID
        which is requested... This function searches possible filenames in the Logo-Folder (defined at top)
        :param stationID: 6454
        :return: True or False if there is no Logo found (locally) for this ID
        """
        for extention in ["png", "jpg", "jpeg"]:

            fileToImport = os.path.join(LogoFolder, "{0}.{1}".format(stationID, extention))

            if os.path.isfile(fileToImport):
                self.lbl_Senderlogo.setPixmap(QPixmap(fileToImport).scaled(self.lbl_Senderlogo.width(),
                                                                       self.lbl_Senderlogo.height(),
                                                                       Qt.KeepAspectRatio, Qt.SmoothTransformation))
                return True
        else:
            logger.warning("There is no File for {0} in LogoFolder {1}".format(stationID, LogoFolder))
            return False

    def mute(self):
        """
        This function stops the player and delete it, (making it garbage collected...) if it is not None anyway
        """
        if self.player is not None:
            if self.mode == "radio":
                self.player.stop()
                self.player = None
            elif self.mode == "media":
                self.player.pause()

    def unmute(self):
        """
        This function is used to start playing when it was muted or in standby
        """
        self.emit(SIGNAL("sig_LCD_on"))
        if not self.audio_amp_isActive:
            self.emit(SIGNAL("sig_audio_amp_on"))

        if not self.tabWidget_main.isEnabled():   # if anything is disabled, set everything enabled ...
            self.tabWidget_main.setEnabled(True)
            self.pBHome.setEnabled(True)
            self.pBSuchen.setEnabled(True)
            self.pBFavoriten.setEnabled(True)
            self.slider_vol.setEnabled(True)
            self.pBVol_down.setEnabled(True)
            self.pBVol_up.setEnabled(True)

        if not self.widget_Mute.isEnabled():    # if mute-btn is not enabled, switch it to enabled
            self.widget_Mute.setEnabled(True)

        if self.mode == "media":
            self.pBZurueck.setVisible(True)
            self.pBZurueck.setEnabled(True)

        if not self.mpd_listener.isrunning():   # if mpd listener was stoped, spawn it again
                self.mpd_listener.startNotifier()

        if self.player is None:                 # if the player instance was deleted ... create a new one.
            logger.warning("player is None...")
            app.processEvents()
            if self.myCurrentStation is not None and self.mode == "radio":
                logger.info("player is None... starting playStationbyID, but i got a myCurrentStation information")
                self.playStationByID(self.myCurrentStation.id)
            elif self.mode == "media" and len(self.playlisteditor.playlist) > 0:
                self.player = MPC_Player()
                self.widget_Mute.unmute()
            else:
                logger.critical("Impossible to unmute because player is None and is not created. Dont know what to do")

        else:                                  # if the player is still existing, restore volume and simply play
            app.processEvents()
            logger.info("Function Unmute: Player is not none... start Playing")
            self.widget_Mute.show_unmute()
            self.player.play()
            self.label.setText(self.tr("now playing ..."))
        if self.volume is not None:
            self.slider_vol.setValue(int(self.player.status("volume")))

    def standby(self):
        """
        If the player is not None, switch of the widgets ... this does not save any power or prozessor usage,
        but suggerates the user, the webradio is "off" now... maybe this should be made in a different way....
        """
        ## NEU #############################################################################################
        dialog = ShutdownDialog(options=[self.tr("Shutdown"),
                                         self.tr("Standby"),
                                         self.tr("Reboot"),
                                         self.tr("Abort")], parent=self)
        dialog.exec_()
        if dialog.exitStatus is None:
            return False
        elif dialog.exitStatus == self.tr("Shutdown"):
            self.close()
            if not args.debug:
                self.systemCall("sudo shutdown -h now")
            else:
                logger.debug(u"Would shutdown now!")
        elif dialog.exitStatus == self.tr("Standby"):
        ######################################################################################################
            if self.player is not None:
                self.widget_Mute.mute()
                #if self.mpd_listener.isrunning():      # this will prevent any ramote applicaten to restart ...
                #    self.mpd_listener.stopNotifier()   # so I can not switch of the daemon, otherwise it can not be
                self.lbl_Senderlogo.setText("")
                self.label.setText("")
                self.lbl_Fav.setText("")
                self.lbl_Fav.installEventFilter(self)
                self.lbl_Sendername.setText("Standby")
                self.lbl_Musiktitel.setText(u"")
                self.pBZurueck.setVisible(False)
                self.tabWidget_main.setEnabled(False)
                self.widget_Mute.setEnabled(False)
                self.pBHome.setEnabled(False)
                self.pBSuchen.setEnabled(False)
                self.pBFavoriten.setEnabled(False)
                self.slider_vol.setValue(0)
                self.slider_vol.setEnabled(False)
                self.pBVol_down.setEnabled(False)
                self.pBVol_up.setEnabled(False)

            if self.audio_amp_isActive:
                self.emit(SIGNAL("sig_audio_amp_off"))
            self.emit(SIGNAL("sig_LCD_off"))
        #########################################################################################################
        elif dialog.exitStatus == self.tr("Reboot"):
            self.close()
            if not args.debug:
                self.systemCall("sudo reboot")
            else:
                logger.debug(u"Would reboot now!")
        elif dialog.exitStatus == self.tr("Abort"):
            # show again the initial state of the button (on)
            # have to use singleshot Timer because otherwise button is changed because of signal
            QTimer.singleShot(20, lambda : self.widget_Standby.setInitialState("on"))

    def askQuestion(self, text1, btn1, text2=None, btn2=None):
        """
        Brings up a custom popup window, with custom Textcontent and buttons.
        :param text1: Topline Text
        :param btn1:  Left Btn Text
        :param text2: Second Line Text
        :param btn2:  Right Btn Text
        :return: 0 (if left Btn was clicked), 1 (if right Btn was clicked)
        """
        text1 = text1
        btn1 = btn1
        msgBox = QMessageBox(self)
        font = QFont()
        font.setPointSize(26)
        msgBox.setFont(font)
        msgBox.setIcon(QMessageBox.Question)
        #msgBox.setText("%s" % text1.decode("utf-8"))
        msgBox.setText(text1)
        if text2 is not None: msgBox.setInformativeText(text2)
        msgBox.addButton(btn1, QMessageBox.ActionRole)                             # ret = 0
        for button in msgBox.findChildren(QPushButton):
            button.setFixedSize(button.sizeHint()*2)
        if btn2 is not None: msgBox.addButton(btn2, QMessageBox.RejectRole)        # ret = 2
        ret = msgBox.exec_()
        ret = int(ret)

        if ret == 0:
            return 0       # Result Button 1 (OK)
        else:
            return 1       # Result Button 2 (Cancel)

    def eventFilter(self, Object, Event):

        if Object == self.lbl_Fav:
            if Event.type() == QEvent.MouseButtonRelease:   # if the user clicked on the favorite-star right of the logo
                logger.info("Toggle favarites status of: %s" % self.myCurrentStation.name)
                self.markAsFavorite()
        if Object == self:
            if Event.type() == QEvent.MouseButtonPress:
                if not self.audio_amp_isActive:
                    logger.info("Amp is not active")
                    self.reanimate_from_standby()

        return False # lets the event continue to the edit

    def closeEvent(self, QCloseEvent):
        logger.info("CloseEvent")

        if self.player is not None:
            logger.info("Stop Player")
            self.player.stop()

        if self.mpd_listener.isrunning():
            logger.info("Stop MPD Listener")
            self.mpd_listener.stopNotifier()

        if self.usb_manager.isrunning():
            logger.info("Stop USB Manager")
            self.usb_manager.stop_notifier()

        if self.mode == "media":
            if self.player != None:
                self.player.save_playlist("media_playlist")      # assure that current playlist is saved...
                logger.info("Saved Media-Playlist")

        logger.info("Destroy Player")
        self.player = None

        logger.info("Save Favorites")
        self.saveFavorites()

        logger.info("Write Settings")
        self.writeSettings()

        logger.info("Save GPIO Presets")
        self.saveGPIO_Presets()

        if GPIO_active:
            try:
                logger.info("Reset GPIOs")
                self.on_audio_amp_off()
                #self.gpio_watchdog.reset_gpios()
            except:
                logger.critical("Reset GPIOs FAILED")
        #print("Now accept event...")
        QCloseEvent.accept()
        if self.shutdowntrigger:
            #print("Now shutdown")
            commands.getoutput("sudo shutdown -h now")

    def dummy(self, arg=None):
        print("DUMMY:")
        print("With Arg:", arg)

    def splash_loading(self, request=False):
        #print("splash called with", request)
        if request:
            #print("Show")
            QTimer.singleShot(40000, self.splash_loading)
            self.splash.raise_()
            self.splash.show()
        else:
            self.splash.close()

    def reanimate_from_standby(self):

        self.emit(SIGNAL("sig_LCD_on"))
        self.reanimation_timer = QTimer()
        self.reanimation_timer.setSingleShot(True)
        self.reanimation_timer.timeout.connect(lambda : self.goback_to_standby())
        #print("Start Timer")
        self.reanimation_timer.start(3000)

    def goback_to_standby(self):
        #print("Going back to Standby")
        if not self.audio_amp_isActive:
            self.emit(SIGNAL("sig_LCD_off"))

    def showStatusBarText(self, text='Bereit', time="10000"):
        #print('STATUS: %s' % text)
        int_time = int(time)
        text = text
        #self.statusbar.showMessage(unicode(text), int_time)

    def add_selection_to_playlist(self, selections):

        try:
            pathes = []
            for selection in selections:
                if self.model.hasChildren(selection):
                    continue  # override pure folders...
                path = self.model.fileInfo(selection).absoluteFilePath()
                pathes.append(path)
            if len(pathes) == 0:
                return False
        except:
            logger.error("No file selected... aborting")
            return False

        #print("TYPE111:", type(pathes[0])) # str
        #print("PATH111", pathes[0])
        #print(unicode(pathes[0]))

        firstIDinPlaylist = self.player.add(unicode(pathes[0]), MusicFolder)

        if len(pathes) > 1:
            for pathesToAdd in pathes[1:]:
                if not self.player.add(unicode(pathesToAdd), MusicFolder):
                    pass
                    #print("file: {0} can not be added".format(pathesToAdd))

        if not firstIDinPlaylist is False:
            pass
            #print("Player added sucessfully '{0}' pathes, "
            #      "the first path '{1} is called to play now (ID:{2}".format(len(pathes),
            #                                                                 pathes[0],
            #                                                                 firstIDinPlaylist))
        return firstIDinPlaylist

    def add_selection_to_playlist_from_search(self, pathes):
        #print("TYPE:", type(pathes[0])) # str
        #print("PATH", pathes[0])
        if len(pathes) == 0:
            return False

        firstIDinPlaylist = self.player.add(os.path.join(MusicFolder,pathes[0]), MusicFolder)
        if len(pathes) > 1:
            for pathesToAdd in pathes[1:]:
                if not self.player.add(os.path.join(MusicFolder,pathesToAdd), MusicFolder):
                    pass
                    #print("file: {0} can not be added".format(pathesToAdd))

        if not firstIDinPlaylist is False:
            pass
            #print("Player added sucessfully '{0}' pathes, "
            #      "the first path '{1} is called to play now (ID:{2}".format(len(pathes),
            #                                                                 pathes[0],
            #                                                                 firstIDinPlaylist))
        return firstIDinPlaylist

    def exchange_model(self):
        #print("Exchanging model...")
        self.myProvider = FileIconProvider()
        self.model = LM_QFileSystemModel()
        self.model.setRootPath(MusicFolder)
        self.model.setIconProvider(self.myProvider)
        self.model.setFilter(QDir.AllEntries|QDir.NoDotAndDotDot|QDir.AllDirs|QDir.Name)
        self.model.setNameFilters(['*.mp3','*.MP3'])

        #self.model.setSorting(QDir.Name|QDir.DirsFirst)
        self.treeView.setModel(self.model)
        self.treeView.setRootIndex(self.model.index(MusicFolder))
        self.treeView.setIconSize(QSize(32,32))
        self.treeView.setAnimated(False)
        self.treeWidget_2.setIconSize(QSize(32,32))
        self.treeWidget_2.setAnimated(False)
        self.model.directoryLoading.connect(lambda : self.splash_loading(True))
        self.model.directoryLoaded.connect(lambda : self.splash_loading(False))

    def systemCall(self, command):
        return_value = sp.Popen(command, shell=True, stdout=sp.PIPE).stdout.read()
        return return_value


class RadioStation(object):

    def __init__(self, name, station_id, url, fav=None, parent=None):
        self.name = name
        self.id = station_id
        self.fav = fav
        self.url = url

    def isFavorite(self):
        return self.fav

    def setAsFavorite(self):
        self.fav = True

    def unsetFavorite(self):
        self.fav = False


class Playlisteditor(object):

    def __init__(self, viewWidget, service, parent=None):
        self.parent = parent
        self.view = viewWidget
        self.service = service
        self.view.setSelectionMode(QAbstractItemView.SingleSelection)
        #self.service = MPC_Player()
        self.playlist = []

    @pyqtSlot()                  # Connect here to "update" the playlist shown...
    def grapCurrentPlaylist(self):
        self.playlist = self.service.get_playlistWithId()
        #print self.playlist
        status = self.service.status("state")
        if status == "play":
            if "songid" in self.service.client.status():
                songID = self.service.status("songid")
            else:
                songID = None
        else:
            status = None
            songID = None

        self.__populate(status, songID)

    def __populate(self, status=None, songID=None):
        selection_to_restore = self.view.selectedIndexes()[0].row() if len(self.view.selectedIndexes()) > 0 else None
        if len(self.playlist) == 0:
            self.view.clear()
            return False
        if self.view.count() > 0: self.view.clear()
        #font = QFont()
        #font.setBold(True)
        #font.setPointSize(14)
        for entry in self.playlist:
            if "title" in entry:
                if entry["title"] != "":
                    key = "title"
                else:
                    key = "file"
            else:
                key = "file"
            #print("for name using key {0}, {1}".format(key, entry[key]))
            itemname = entry[key].decode('utf-8') if key == "title" else entry[key].split("/")[-1:][0].decode('utf-8')
            #print(itemname)
            item = QListWidgetItem(itemname)
            item.setTextAlignment(Qt.AlignRight)
            item.setData(Qt.UserRole, [entry["id"], entry["pos"]])
            item.setSizeHint(QSize(10,35))
            #item.setFont(font)
            if entry["id"] == songID:
                item.setIcon(QIcon(":/play.png"))
            self.view.addItem(item)
        if selection_to_restore is not None:
            self.view.setCurrentRow(selection_to_restore)

    @pyqtSlot()                                # Connect here the function button "up"
    def moveItemUp(self):
        #print("Move Up")
        item = self.view.selectedIndexes()[0] if len(self.view.selectedIndexes()) > 0 else None
        if item is not None:
            selectionBackup = item.row()
            ID_to_move, pos = item.data(Qt.UserRole).toStringList()
            if (int(pos) -1) == -1: return False
            #print("Moving id '{0}' up to position '{1}'".format(ID_to_move, int(pos) -1))
            self.service.client.moveid(int(ID_to_move), int(pos) -1)
            self.grapCurrentPlaylist()
            self.view.setCurrentRow(selectionBackup -1)
        else:
            print("No Item selected")

    @pyqtSlot()                                # Connect here the function button "down"
    def moveItemDown(self):
        #print("Move down")
        item = self.view.selectedIndexes()[0] if len(self.view.selectedIndexes()) > 0 else None
        if item is not None:
            selectionBackup = item.row()
            ID_to_move, pos = item.data(Qt.UserRole).toStringList()
            if (int(pos)+1) == self.view.count(): return False
            #print("Moving id '{0}' down to position '{1}'".format(ID_to_move, int(pos) +1))
            self.service.client.moveid(int(ID_to_move), int(pos) +1)
            self.grapCurrentPlaylist()
            self.view.setCurrentRow(selectionBackup +1)
        else:
            print("No Item selected")

    @pyqtSlot()                                 # Connect here the function button "delete"
    def deleteItem(self):
        items = self.view.selectedIndexes()
        if len(items) == 0:
            return
        for item in items:
            selectionBackup = item.row()
            ID_to_delete, pos = item.data(Qt.UserRole).toStringList()
            self.service.client.deleteid(ID_to_delete)
            item_to_pop = self.view.itemFromIndex(item)
            self.view.removeItemWidget(item_to_pop)
            if not selectionBackup > self.view.count():
                self.view.setCurrentRow(selectionBackup)
            self.view.setSelectionMode(QAbstractItemView.SingleSelection)
        QApplication.processEvents()
        self.grapCurrentPlaylist()

    def tellMeWhatsPlaying(self):
        self.grapCurrentPlaylist()
        #print("I tell you what playing is !!!")
        currentID = self.service.status("songid")
        nextID = self.service.status("nextsongid")
        previouse = ""
        current = ""
        next = ""
        playlist_ID_POS = {}
        playlist_POS_ID = {}
        playlist_POS_TITLE = {}
        #print("Current ID is:", currentID)
        #print("Next ID is:", nextID)
        for i in range(self.view.count()):
            songtitle = self.view.item(i).text()
            ID = self.view.item(i).data(Qt.UserRole).toStringList()[0]
            pos = self.view.item(i).data(Qt.UserRole).toStringList()[1]
            playlist_ID_POS[ID] = pos
            playlist_POS_ID[pos] = ID
            playlist_POS_TITLE[pos] = songtitle

            #print(playlist_ID_POS)
            #print(playlist_POS_ID)
            #print(playlist_POS_TITLE)

            #print("check pos", pos)
            #if ID == currentID:
            #    current= songtitle
            #    print("setting current to", songtitle)
            #    continue
            #elif ID == nextID:
            #    next = songtitle
            #    print("setting next to", songtitle)
            #    #break
            #if next == "" or str(pos) == "0":
            #    previouse = songtitle

        #if currentID == "" and nextID == "" and self.view.count() > 0:
        #    print("Im in if statement... changing next from", next)
        #    print("Changing also previouse from ... to empty ", previouse)
        #    next = self.view.item(0).text()
        #    previouse = ""
        if currentID != "":
            previouse_pos = int(playlist_ID_POS[QString(currentID)]) -1
            #print("Previos position:", previouse_pos)
            if previouse_pos < 0 and self.parent.pB_autorepeat.isChecked():
                # only if autorepeat is on
                previouse_pos = self.view.item(self.view.count()-1).data(Qt.UserRole).toStringList()[1]
                #print("new previos position:", previouse_pos)
                previouse = playlist_POS_TITLE[previouse_pos]
            elif previouse_pos >= 0:
                previouse = playlist_POS_TITLE[QString(str(previouse_pos))]
            else:
                previouse=QString("")

            current = playlist_POS_TITLE[playlist_ID_POS[QString(currentID)]]
        if nextID != "":
            next = playlist_POS_TITLE[playlist_ID_POS[QString(nextID)]]

        #print("sending song infos", previouse, current, next)
        return [previouse, current, next]


class WorkerThread(QThread):
    def __init__(self, function, *args, **kwargs):
        QThread.__init__(self)
        self.function = function
        self.args = args
        self.kwargs = kwargs

    #def __del__(self):
    #    self.wait()

    def run(self):
        self._result = None
        self._result = self.function(*self.args,**self.kwargs)
        return

    def result(self):
        return self._result


class AnimatedSplashScreen(QSplashScreen):

   def __init__(self, animation):
       # run event dispatching in another thread
       QSplashScreen.__init__(self, QPixmap())
       self.movie = QMovie(animation)
       #self.movie.setSpeed(100)
       #self.movie.setCacheMode(QMovie.CacheAll)
       self.connect(self.movie, SIGNAL('frameChanged(int)'), self.onNextFrame)
       self.movie.start()

   @pyqtSlot()
   def onNextFrame(self):
       pixmap = self.movie.currentPixmap()
       self.setPixmap(pixmap)
       self.setMask(pixmap.mask())


class FileIconProvider(QFileIconProvider):

    def __init__(self):
        QFileIconProvider.__init__(self)

    def icon(self, arg):
        #print("ARG", arg.completeSuffix())
        #QFileInfo.isSymLink()
        if arg.completeSuffix() == "mp3" or arg.completeSuffix() == "MP3":
            return QIcon(":/mp3.png")
        elif arg.isDir():
            #print("isDir")
            if arg.symLinkTarget() != "":
                #print("Target is:", arg.symLinkTarget())
                if os.path.ismount(str(arg.symLinkTarget())):
                    #print("isMounted")
                    return QIcon(":/connected.png")
                else:
                    #print("is not Mounted")
                    return QIcon(":/disconnected.png")
            return  QIcon(":/folder.png")
        elif arg.isSymLink():
            #print("isSymlink")
            if arg.symLinkTarget() != "":
                #print("Target is:", arg.symLinkTarget())
                if os.path.ismount(str(arg.symLinkTarget())):
                    #print("isMounted")
                    return QIcon(":/connected.png")
                else:
                    #print("is not Mounted")
                    return QIcon(":/disconnected.png")
            return  QIcon(":/folder.png")
        else:
            return QIcon(":/mp3.png")


class ShutdownDialog(QDialog):

    # this class brings up a modal window from where the user can select diffent options
    def __init__(self, text="", options=[], parent=None):
        super(ShutdownDialog, self).__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setStyleSheet("QDialog {"
                               #"background-image: url(:/webradio-main.png);"
                               "background-color: rgb(76, 76, 76);"
                               "color: rgb(240, 240, 240);"
                               "}")
        # estimate available size on the screen:
        if parent is None:
            screensize = QDesktopWidget().screenGeometry()
        else:
            screensize = parent.geometry()
        # construct window:
        layout = QVBoxLayout()
        if text != "":
            lbl = Scaling_QLabel()
            lbl.setWordWrap(True)
            lbl.setText(text)
            layout.addWidget(lbl)

        for option in options:
            btn = QPushButton(option)
            btn.setFixedHeight(screensize.height()/len(options)*0.5)
            font = btn.font()
            font.setPointSize(32)
            btn.setFont(font)
            btn.clicked.connect(self.on_btn_clicked)
            layout.addWidget(btn)

        self.setLayout(layout)
        # set size of the modal window:
        self.setFixedWidth(screensize.width()*0.7)
        # move modal window to center ?
        #self.move((screensize.width()-self.geometry().width())/2,
        #          (screensize.height()-self.geometry().height())/2)
        self.exitStatus = None

    def on_btn_clicked(self):
        #print("React on btn: {0}".format(self.sender().text()))
        self.exitStatus = self.sender().text()
        self.accept()


if __name__ == "__main__":

    ####################################Start GUI #########################################
    app = QApplication(sys.argv)
    app.setOverrideCursor(QCursor(Qt.BlankCursor))     # new - testing
    language = unicode(QLocale.system().name())
    qtTranslator = QTranslator()
    qtTranslator.load("qt_{0}".format(language), QLibraryInfo.location(QLibraryInfo.TranslationsPath))
    app.installTranslator(qtTranslator)

    mytranslator = QTranslator()
    mytranslator.load("local_{0}".format(language), os.path.join(cwd, "locale"))
    app.installTranslator(mytranslator)

    splash = QSplashScreen(QPixmap(":/loading_wall.png"))
    splash.show()
    app.processEvents()

    sizeString = global_vars.configuration.get("GENERAL").get("screen_resolution")
    if sizeString is None or "x" not in sizeString:
        logger.warning(u"No Screen-Resolution defined in Config-Files or in wrong Format: {0}, "
                       u"setting default Screenresolution (1024x600)".format(sizeString))
        sizeString = "1024x600"
    width, height = sizeString.rstrip().split("x")
    mainwindow = MainWindow(QSize(int(width), int(height)))

    mainwindow.startup_actions()
    mainwindow.show()
    splash.finish(mainwindow)
    if args.fullscreen:
        mainwindow.showFullScreen()     # a fullscreen window at raspberry is 1024 x 600 (Splashscreen does not work ?)

    app.exec_()

'''
Verison History:

0.0.1   -Erste funktionierende Version
0.0.2   -Rudimentär steuerbar über Android Apps (mpd)
0.0.3   -Code strukturiert und kommentiert
        -/lib/players wurde zum mpd-client und setzt nicht nur "dumme" Befehle an die Shell ab
        -durch die Änderung an der Player-Klasse ist nun auch das Problem weg, dass sich Befehle überschlagen und es
         dadurch zu "broken Pipes" zum mpd hin kommt.
        -mpd buffer wurde aktiviert (zumindest versuchshalber auf dem Pi, siehe Readme.txt.)
        -loop in www.radio.de API hinterlegt, um "sicheren" Download von Informationen zu gewährleisten
        -logging implementiert
0.0.4   -UI umdesigned um "Media-Reiter" einzuführen (Tabwidget)
        -Lautstärkenreger implementiert (Funktionsfähig)
        -MPD-Daemon um signal "volume_changed()" erweitert
        -Rudimentäres abspielen von MP3 Dateien über Media-Reiter implementiert
        -Weitere Kommentare hinzugefügt
0.0.5   -Media Player kann nun Files abspielen die selektiert sind, des weiteren added er alle weiteren Dateien in
         der File-Struktur in die Playlist.
        -Die Markierung im TreeView wird verschoben sobald der Song gewechselt wird. (es ist immer der Track markiert,
         der z.Z. gespielt wird.
        -Ui Änderung auf V7
0.0.6   -Playlisteditor (move up/down, remove), der momentan gespielte Track wird markiert, bzw. ein "play"
         icon angezeigt
        -neues Signal aus dem mpd-listener implementiert (playlist changed) um remote Zugriffe / Änderungen
         an der Playlist zu registrieren.
        -kleinere Bug.Fixes
        -für die Radio.de API wurde ein neuer User-Agend eingeführt (XMBC app) da der benutzte nicht mehr zu
         funktionieren scheint.
        -exception handling wenn radio.de nicht rechtzeitig antwortet (z.B. down ist) jedoch internetverbindung besteht.
         Nun wird in einem solchen Fall die URL aus den geladenen Favorites dicts gezogen und versucht ab zu spielen.
         Das Logo wird lokal geladen.
0.0.7   -Kommentare für weitere Funktionen hinzugefügt.
        -Mute/Unmute für Media-Player angepasst ... Standby auch.
        -Stylesheet für Scrollbars (vertical) eingesetzt... größer und in Style-Farbe
        -UI9 eingeführt, zusätzliche Buttons in der Media Playlist (back, stop, play, next)
        -modi können per remote gewechselt werden... je nachdem welche Datei abgespielt wird (http oder mp3) schaltet
         der Player automatisch um und wechselt in die richtige Ansicht, und spielt das übergebene Objekt ;-)
        -UI10 eingeführt ... dieses kann im Vollbildmodus verwendet werden und ist grundsätzlich für den RPI gedacht.
         für den Laptopbetrieb bleibt UI9
0.0.8   -Implementierung rotary via GPIO (gpio_watchdog) (sudo wird nun bei der Ausführung benötigt!!!)
         zur Lautstärkenregelung
        -Implementierung der GPIO Taster (diese senden nun über den gpio_watchdog ein Signal aus >> pressed/released)
        -Implementierung Wetter-Forcast Widget als 3ter Tab im Tabwidget.
        -UI11 eingeführt (Wetter-tab)
        -Presets für GPIOs implementiert (kurz drücken für Sender auswählen, lang drücken um Sender auf Taste zu
         programmieren)
        -Überschriftsmanagement auf eine Function reduziert
        -Virtual Keyboard touch-tauglich gemacht >> Taster werden bei Klick "groß" und nach 500 ms, wieder "klein"
        -Zusätzliches Start-Argument "disable-gpio" eingeführt, damit kann sowohl der GPIO Simulator, als auch der
         GPIO Watchdog unterdrückt werden kann (z.B. für einen Betrieb an einem Laptop, also kein Rapi)
0.0.9   -USB Manager implementiert (signal connected / disconnected), Möglichkeit des "unmount"
0.1.0   -div. Bugfixes
        -Wetter Widget läuft nun viel schneller
        -Splash Screen implementiert (zum Anzeigen von längeren Ladevorgängen)
        -Display on/off in Standbymode implementiert
0.1.1   -Implementierung von aktualisierter Status-Bar
        -Farbe Vertical Scrollbar korrigiert (war nicht mehr sichtbar)
        -Anzeige aktuell wiedergegebener Track im Media player vergrößert
        -Anzeige der Uhr vergrößert, bei längeren Uhrzeiten war das "r" von "Uhr" nicht mehr zu sehen
        -Anzeige im Playlisteditor zeigt nicht den aktuell wiedergegebene Track (Kein Icon / Keine Markierung)
        -Fenster wurde 2 Pixel nach oben geschoben, da es einen minimalen Strich am Pi gab
        -*** Radio: Bei Auswahl eines Tracks muss die Markierung sofort aktualisiert werden, da man sonst denkt man hat
                    danebengedrückt
                    >> ItemClicked in Connections geändert in ItemPressed (schneller)
                    >> Bei on_Item_Clicked, wird das Item nun markiert und auf allen verbundenn ListWidget ein repaint
                       ausgeführt. (Noch nicht auf dem Pi getestet...) --- > bringt nix
        -Radio: "spielt gerade" kommt nach dem Standby nicht mehr. gefixed
        -Weatherwidget: "Statische" Bilder vorscalliert, damit die Ladezeit noch weiter optimiert wird.
        -"touchscreen" ist nun als Argument übergebbar wird dies nicht übergeben bleibt der Mauszeiger sichtbar.
        -Beim Splashscreen während des Programmstarts ist der Mauszeiger unsichtbar,
         damit dieser nicht erkennbar über "loading" steht.
        - Hässliche Icons in TreeView ersetzen (Icon-set installieren, da Standard-Icons verwendet werden)
        - webradio, usb_manager, weatherwidget ersetzen ....
        - logging der volume informationen beschränkt. Nun werden nur noch exceptions gelogged ... ansonsten schreibt
          er bei jedem % das (z.B. über den Rotary-Encoder) verändert wird eine Zeile in den Log.
0.1.2   - Flickcharm implementiert (kinetic scrolling) in ListWidgets
        - Icongröße in Treewidget vergrößert
        - kleinere Fehler beseitigt
        - FileIconProvider implementiert ... (für symbole im Treeview)
        - Flickcharm auf RPI optimiert, da beim klicken immer ein kleiner offset entstand, wodurch flickcharm dachte
          dass es sich um eine scroll-action handelte, was dazu führte, dass der klick "geschluckt" wurde. -fixed
        - Eigenes TreeView mit spezieller Markierungslogik eingeführt
        - Wetter-Widget weiter optimiert (Layout-Themen, anzeige von 3-Stelligen Regenwahrscheinlichkeiten)
        - Flickcharm weiter optimiert. (Toleranzbereich für "click" erweitert und Scrollgeschwindigkeit angpasst)
        - QDirmodel mit QFilesystemmodel ersetzt. Model customized (/lib/mpd_filesystemview)
        - USB_Connected und disconnected mit neuer Funktion verknüpft, da Model jedesmal nochmal geladen werden muss
          um Filesystem neu zu initialisieren.
        - Optische Anzeigen ob ftp-server oder usb-device verbunden sind oder nicht
0.1.3   - implementierung einer searchengine um die MPD Datenbank zu durchsuchen (Media-Player)
        - Virtual Keyboard um Zahlen erweitert
        - div. UTF-8 Probleme bein Hinzufügen von Dateien zur Playliste behoben. (Treewidget, Treeview, ListWidget
          databasesearcher
        - USB Stick kann aus dem Media-Player Modus nicht ausgeworfen werden > behoben
        - Im Media-Player Modus verschwindet der "suchen" Button nach einem Standby > behoben
0.1.4   - VERWORFEN (Youtube hat API-V2 Unterstützung eingestellt, ab sofort darf nur noch API-V3 verwendet werden...)
0.1.5   - Implamentierung eines System-Tests und entsprechender Anpassung der Aktiven Teile des Programms.
0.2.0   - Auslagerung der benutzerspezifischen Einstellungen in eine externe ini Datei (webradio.conf)
        - Erweitertes Standby-Menü. Nun kann man nicht nur Stumm-Schalten und den Datenverkehr abschalten sondern auch
          herunterfahren, Rebooten und natürlich abbrechen.
        - Erweiterte Logfiles (.log = aktuelle Sitzung, .log.1 = letzte Sitzung)
0.2.1   - Unterstuetzung meherer Auflösungen 640x480 - 1024x600
        - automatisch scallierende QLabels und QPushButtons um Layoutgröße zu ermöglichen
0.2.2   - Sleep-Timer (Zeit bis Shutdown...), 10 Sekunden Frühwarnung
0.2.3   - Uebersetzung, Basisversion "English", Uebersetzungspaket de_DE (Deutsch/German) angelegt.
0.2.4   - Installer und Einrichtungsasistent
'''

'''
ISSUES:


Future Functions:
- Icon Sleep-Timer-Tab
- Settings Tab (Language, Weather-Code incl. Search-Func., Background/Design)
'''







