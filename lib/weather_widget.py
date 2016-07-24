#!/usr/bin/python
# -*- coding: utf-8 -*-

import pyqapi as weather
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import urllib2
import os
import sys
from weather_widget_ui import Ui_Form as ui
import global_vars
#cwd = os.path.dirname(os.path.realpath(__file__))      # gives the path, where the script is located
#LOCATION_ID = "GMBY7640"   # Sattelpeilnstein
#LOCATION_ID = global_vars.configuration.get("GENERAL").get("weather_locationid")
#self.WEATHER_ICONS_FOLDER = os.path.join(cwd, "/res/weather/icon/")
#self.WEATHER_ICONS_FOLDER = "/home/matthias/PycharmProjects/Projects/Raspi_WebRadio/res/weather/icon"

dayend_definition = QTime(19,0,0)     # Day ends at 19.00

class weather_widget(QWidget, ui):

    def __init__(self, cwd, parent=None):
        QWidget.__init__(self, parent)
        self.tr("Monday")
        self.tr("Tuesday")
        self.tr("Wednesday")
        self.tr("Thursday")
        self.tr("Friday")
        self.tr("Saturday")
        self.tr("Sunday")
        self.failedConnections = 0
        self.setupUi(self)
        #self.setStyleSheet("QWidget {"
                               #"background-color: rgb(76, 76, 76);"
                               #"color: rgb(240, 240, 240);"
        #                       "}")
        self.lastUpdate = None
        #print("Received: ", cwd)
        self.LOCATION_ID = "GMXX0007"   # Berlin is default
        self.LOCATION_NAME = "Berlin"
        self.load_LOCATIO_ID_from_global_vars() # read location ID from Settings if not None.. otherwise do nothing

        self.WEATHER_ICONS_FOLDER = os.path.join(cwd, "res/weather/icon")
        #print("ICONFOLDER:", self.WEATHER_ICONS_FOLDER)
        QTimer.singleShot(0,self.update_widget)

    def __service_available(self):
        #print("Check if service is available")
        try:                                                             # check internet-connection (call Google.com)
            urllib2.urlopen('http://www.weather.com/',timeout=1)
            print("Yes it is...")
            return True
        except urllib2.URLError:                                         # if there is an error
            print("ERROR: Service is not available !!!")
            self.failedConnections += 1
            return False

    def __update_weatherdata(self):

        if self.lastUpdate == None:
            #print("Update Weather data because of None")
            #self.emit(SIGNAL("start_loading"))
            if self.__service_available():
                self.weatherdata = weather.get_weather_from_weather_com(self.LOCATION_ID)
                #self.emit(SIGNAL("stop_loading"))
                self.lastUpdate = [QTime.hour(QTime.currentTime()), QTime.minute(QTime.currentTime())]
                return True, True
            else:
                self.lastUpdate = None
                return False, True
        elif self.lastUpdate[0] < QTime.hour(QTime.currentTime()) or \
                        self.lastUpdate[1] < (QTime.minute(QTime.currentTime()) -10):
            #print("Update Weather data because of long periode without update")
            self.emit(SIGNAL("start_loading"))
            if self.__service_available():
                self.weatherdata = weather.get_weather_from_weather_com(self.LOCATION_ID)
                self.emit(SIGNAL("stop_loading"))
                self.lastUpdate = [QTime.hour(QTime.currentTime()), QTime.minute(QTime.currentTime())]
                return True, True
            else:
                self.lastUpdate = None
                return False, True
        else:
            #print("It is just a few minutes ago that i updated the weather data... not again :-)")
            return True, False # Data is up to date, available but with no changes...
        ###########

    def update_widget(self):
        weatherDataUpToDate, changes = self.__update_weatherdata()
        if weatherDataUpToDate:
            if not changes:
                #print("No Changes... do not repopulate the icons...")
                return
            ############################################Current Condition#############################################
            print("Startpopulating", QTime.currentTime())
            self.lbl_cur_icon.setPicturePath(os.path.join(self.WEATHER_ICONS_FOLDER,
                                                       self.weatherdata['current_conditions']['icon']))
            self.lbl_cur_temp.setText(self.weatherdata['current_conditions']['temperature'])
            self.lbl_cur_temp_feel.setText(self.weatherdata['current_conditions']['feels_like'])

            if QTime.currentTime() < dayend_definition:
                possible_rain=int(self.weatherdata['forecasts'][0]['day']['chance_precip'])
                self.lbl_cur_rain.setText(str(possible_rain) if possible_rain != 100 else "99")
            else:
                possible_rain= int(self.weatherdata['forecasts'][0]['night']['chance_precip'])
                self.lbl_cur_rain.setText(str(possible_rain) if possible_rain != 100 else "99")

            windspeed = self.weatherdata['current_conditions']['wind']['speed']
            if windspeed == "calm" or windspeed == "CALM":
                windspeed = "0"
            self.lbl_cur_wind.setText(windspeed)
            winddirection = self.weatherdata['current_conditions']['wind']['text']
            if winddirection == "calm" or winddirection == "CALM":
                winddirection = "--"
            self.lbl_cur_wind_direction.setText('"{0}"'.format(winddirection))
            self.lbl_cur_sunrise.setText(self.weatherdata['forecasts'][0]['sunrise'])
            self.lbl_cur_sunset.setText(self.weatherdata['forecasts'][0]['sunset'])
            ########################################## Forcast Area ##################################################
            ###############################Day 1 #####################################################################
            self.label_15.setText(self.tr(self.weatherdata['forecasts'][0]['day_of_week']))
            self.lbl_day_0_icon.setPicturePath(os.path.join(self.WEATHER_ICONS_FOLDER,
                                                       self.weatherdata['forecasts'][0]['day']['icon'],"static"))
            self.lbl_night_0_icon.setPicturePath(os.path.join(self.WEATHER_ICONS_FOLDER,
                                                       self.weatherdata['forecasts'][0]['night']['icon'],"static"))
            self.lbl_day_0_temp.setText(self.weatherdata['forecasts'][0]['high'])
            possible_rain0_day = int(self.weatherdata['forecasts'][0]['day']['chance_precip'])
            self.lbl_day_0_rain.setText(str(possible_rain0_day) if possible_rain0_day != 100 else "99")
            self.lbl_night_0_temp.setText(self.weatherdata['forecasts'][0]['low'])
            possible_rain0_night = int(self.weatherdata['forecasts'][0]['night']['chance_precip'])
            self.lbl_night_0_rain.setText(str(possible_rain0_night) if possible_rain0_night != 100 else "99")
            ###############################Day 2 #####################################################################
            self.label_16.setText(self.tr(self.weatherdata['forecasts'][1]['day_of_week']))
            self.lbl_day_1_icon.setPicturePath(os.path.join(self.WEATHER_ICONS_FOLDER,
                                                       self.weatherdata['forecasts'][1]['day']['icon'],"static"))
            self.lbl_night_1_icon.setPicturePath(os.path.join(self.WEATHER_ICONS_FOLDER,
                                                       self.weatherdata['forecasts'][1]['night']['icon'],"static"))
            self.lbl_day_1_temp.setText(self.weatherdata['forecasts'][1]['high'])
            possible_rain1_day = int(self.weatherdata['forecasts'][1]['day']['chance_precip'])
            self.lbl_day_1_rain.setText(str(possible_rain1_day) if possible_rain1_day != 100 else "99")
            self.lbl_night_1_temp.setText(self.weatherdata['forecasts'][1]['low'])
            possible_rain1_night = int(self.weatherdata['forecasts'][1]['night']['chance_precip'])
            self.lbl_night_1_rain.setText(str(possible_rain1_night) if possible_rain1_night != 100 else "99")
            ###############################Day 3 #####################################################################
            self.label_17.setText(self.tr(self.weatherdata['forecasts'][2]['day_of_week']))
            self.lbl_day_2_icon.setPicturePath(os.path.join(self.WEATHER_ICONS_FOLDER,
                                                       self.weatherdata['forecasts'][2]['day']['icon'],"static"))
            self.lbl_night_2_icon.setPicturePath(os.path.join(self.WEATHER_ICONS_FOLDER,
                                                       self.weatherdata['forecasts'][2]['night']['icon'],"static"))
            self.lbl_day_2_temp.setText(self.weatherdata['forecasts'][2]['high'])
            possible_rain2_day = int(self.weatherdata['forecasts'][2]['day']['chance_precip'])
            self.lbl_day_2_rain.setText(str(possible_rain2_day) if possible_rain2_day != 100 else "99")
            self.lbl_night_2_temp.setText(self.weatherdata['forecasts'][2]['low'])
            possible_rain2_night = int(self.weatherdata['forecasts'][2]['night']['chance_precip'])
            self.lbl_night_2_rain.setText(str(possible_rain2_night) if possible_rain2_night != 100 else "99")

            #print("End Polulating", QTime.currentTime())

        else:
            #print("Setting Fallback")
            ############################################Current Condition#############################################
            self.lbl_cur_icon.setPicturePath(os.path.join(self.WEATHER_ICONS_FOLDER,""))
            self.lbl_cur_temp.setText("--")
            self.lbl_cur_temp_feel.setText("--")
            self.lbl_cur_rain.setText("--")
            self.lbl_cur_wind.setText("--")
            self.lbl_cur_wind_direction.setText("--")
            self.lbl_cur_sunrise.setText("--")
            self.lbl_cur_sunset.setText("--")
            ########################################## Forcast Area ##################################################
            ###############################Day 1 #####################################################################
            self.label_15.setText(" No Connection ")
            self.lbl_day_0_icon.setPicturePath(os.path.join(self.WEATHER_ICONS_FOLDER,""))
            self.lbl_night_0_icon.setPicturePath(os.path.join(self.WEATHER_ICONS_FOLDER,""))
            self.lbl_day_0_temp.setText("--")
            self.lbl_day_0_rain.setText("--")
            self.lbl_night_0_temp.setText("--")
            self.lbl_night_0_rain.setText("--")
            ###############################Day 2 #####################################################################
            self.label_16.setText(" No Connection ")
            self.lbl_day_1_icon.setPicturePath(os.path.join(self.WEATHER_ICONS_FOLDER,""))
            self.lbl_night_1_icon.setPicturePath(os.path.join(self.WEATHER_ICONS_FOLDER,""))
            self.lbl_day_1_temp.setText("--")
            self.lbl_day_1_rain.setText("--")
            self.lbl_night_1_temp.setText("--")
            self.lbl_night_1_rain.setText("--")
            ###############################Day 3 #####################################################################
            self.label_17.setText(" No Connection ")
            self.lbl_day_2_icon.setPicturePath(os.path.join(self.WEATHER_ICONS_FOLDER,""))
            self.lbl_night_2_icon.setPicturePath(os.path.join(self.WEATHER_ICONS_FOLDER,""))
            self.lbl_day_2_temp.setText("--")
            self.lbl_day_2_rain.setText("--")
            self.lbl_night_2_temp.setText("--")
            self.lbl_night_2_rain.setText("--")

            if self.failedConnections < 3:
                QTimer.singleShot(10000, self.update_widget())
            else:
                self.failedConnections = 0
                QTimer.singleShot(100000, self.update_widget())
                #print("No Connection to weathersurver possible delay ")

        self.update()

    def load_LOCATIO_ID_from_global_vars(self):
        if global_vars.configuration.get("GENERAL").get("weather_locationid") is not None:  # act only if loc-code is
            self.LOCATION_ID = global_vars.configuration.get("GENERAL").get("weather_locationid") # not None
            if global_vars.configuration.get("GENERAL").get("weather_locationname") is not None:
                self.LOCATION_NAME = global_vars.configuration.get("GENERAL").get("weather_locationname")
            else:
                self.LOCATION_NAME = ""

    def get_LocationId_for(self, cityname):
        '''
        Use: weather.get_loc_id_from_weather_com("Berlin")
        Args:
            cityname: String
        Returns: {<ID> : <"Loc_id", "Cityname and Location">,...count: <int>}
            {0: (u'GMXX0007', u'Berlin, BE, Germany'),
             1: (u'USGA0048', u'Berlin, GA'),
             2: (u'USIL1340', u'Berlin, IL'),
             3: (u'USMD0033', u'Berlin, MD'),
             4: (u'USMA0038', u'Berlin, MA'),
             5: (u'USND0032', u'Berlin, ND'),
             6: (u'USNH0020', u'Berlin, NH'),
             7: (u'USNJ0041', u'Berlin, NJ'),
             8: (u'USNY0115', u'Berlin, NY'),
             9: (u'USPA0117', u'Berlin, PA'),
             'count': 10}
        '''
        return weather.get_loc_id_from_weather_com(cityname)




if __name__ == "__main__":
    app = QApplication([])

    weatherWindow = weather_widget()
    weatherWindow.show()
    weatherWindow.update_widget()

    sys.exit(app.exec_())








