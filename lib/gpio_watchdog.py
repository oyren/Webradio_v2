#!/usr/bin/env python
# -*- coding: utf-8 -*-
################################
# Whatchdog for monitoring Raspberry Pi GPIO Status
# even a defined event occured on one or more inputs / outputs, a signal will be emitted.
# for example, see Window-Class at the end of this file
#
# IMPORTANT: This script has to be executed as root, use sudo or gksudo
################################

import RPi.GPIO as GPIO
import Adafruit_DHT
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import logging
import time
import global_vars

logger = logging.getLogger("webradio")

pins_in_use = {}
for pin in global_vars.configuration.get("GPIOS_IN").itervalues():
    try:
        pins_in_use.update({int(pin): [GPIO.IN, GPIO.BOTH]})
    except (ValueError, TypeError), e:
        logger.error(u"Der GPIO_IN '{0}' ist ungültig! {1}".format(pin.decode("utf-8"), e))

for pin in global_vars.configuration.get("GPIOS_OUT").itervalues():
    try:
        pins_in_use.update({int(pin): [GPIO.OUT, None]})
    except (ValueError, TypeError), e:
        logger.error(u"Der GPIO_IN '{0}' ist ungültig! {1}".format(pin.decode("utf-8"), e))

# Define GPIO inputs for rotary Encoder, if one is in use, else tell variables to be "None"

try:
    PIN_A = int(global_vars.configuration.get("ROTARY_ENCODER").get("pin_a")) # brown wire
    PIN_B = int(global_vars.configuration.get("ROTARY_ENCODER").get("pin_b")) # white wire
except (ValueError, TypeError), e:
    logger.warning(u"Ein Rotary-Encoder Pin ist ungültig! {0}".format(e))
    PIN_A = None
    PIN_B = None

BUTTON = 22 # brown wire (2)  -> Button is not in use,

tempsensor = Adafruit_DHT.DHT11
try:
    GPIO_TEMP = int(global_vars.configuration.get("DHT11").get("gpio_temp")) # give the GPIO not the Pin-No
    delay_tempmeasurement = int(global_vars.configuration.get("DHT11").get("delay_tempmeasurement"))
except (ValueError, TypeError), e:
    logger.warning(u"Der GPIO oder die Sekundenangabe für den Delay ist ungültig! {0}".format(e))
    GPIO_TEMP = None
    delay_tempmeasurement = 180


class Gpio_Watchdog(QObject):

    def __init__(self, parent=None):
        QObject.__init__(self, parent)
        self.gpio_states={}
        self.initReady = False
        self.__initGPIOs()
        self.rswitch = RotaryEncoder(PIN_A,PIN_B,None,self.switch_event, parent=self)
        self.initReady = True
        self.reset_timer = QTimer()
        self.reset_timer.setSingleShot(True)
        self.reset_timer.timeout.connect(lambda : self.assure_gpio_states_are_resetted())

        if GPIO_TEMP is not None:
            self.worker = WorkerThread(self.startup_temperature_sensing)
            self.worker.start()

    def __initGPIOs(self):
        #setup GPIO using Board numbering (pins, not GPIOs)
        GPIO.setwarnings(False)
        GPIO.cleanup()
        GPIO.setmode(GPIO.BOARD)

        #setup defined pins and event_detectors or outputs and initial states (initial is always 0, low)
        for pin in pins_in_use:
            if pins_in_use[pin][0] == GPIO.IN:
                if pin == 5:
                    GPIO.setup(pin, pins_in_use[pin][0], pull_up_down=GPIO.PUD_UP)
                else:
                    GPIO.setup(pin, pins_in_use[pin][0])
                GPIO.add_event_detect(pin, pins_in_use[pin][1], callback=self.shoutItOut, bouncetime=100)
                self.gpio_states.update({pin: 1})
            elif pins_in_use[pin][0] == GPIO.OUT:
                GPIO.setup(pin, pins_in_use[pin][0], initial=0)

    def shoutItOut(self, channel):
        logger.info("Channel: {0}, got falling Flank".format(channel))

        self.reset_timer.stop()
        if not self.initReady:
            logger.info("Channel: {0}, ignoring because of init not ready".format(channel))
            return
        force_newState = None
        activated = 0
        for i in range(10):
            time.sleep(.001)
            activated += GPIO.input(channel)
            print(activated)
        if activated is 10:
            force_newState=1
            #logger.debug("new State is 1, because all measured values were 1")
        elif activated < 5:
            force_newState=0
            #logger.debug("new State is 0, because all measured values were 0")

        if channel in self.gpio_states:
            lastState = self.gpio_states[channel]
            if force_newState is not None:
                if lastState is force_newState:
                    logger.debug("ignoring, because of force {0}".format(force_newState))
                    return
                newState = force_newState
            else:
                if lastState == 0:
                    newState = 1
                else:
                    newState = 0
            self.gpio_states.update({channel: newState})  #only inputs are included in this dict.

            if self.gpio_states[channel] == 1:
                self.emit(SIGNAL("gpio_button_released"), channel)
            else:
                self.emit(SIGNAL("gpio_button_pressed"), channel)

            self.reset_timer.start(5000) # assure after 5 seconds, that last state is "released"
        return

        #if GPIO.input(channel):
        #    self.emit(SIGNAL("gpio_button_released"), channel)
        #else:
        #    self.emit(SIGNAL("gpio_button_pressed"), channel)
        #return

    def assure_gpio_states_are_resetted(self):

        logger.debug("resetting last states of swithes")
        for entry in self.gpio_states.iterkeys():
            self.gpio_states.update({entry: 1})   # Switches are 1 if the are released ....


    def switch_event(self, event):
        if event == RotaryEncoder.CLOCKWISE:
            self.emit(SIGNAL("gpio_rotary_turned"), "clockwise")
            #print("clockwise")
        elif event == RotaryEncoder.ANTICLOCKWISE:
            self.emit(SIGNAL("gpio_rotary_turned"), "anticlockwise")
            #print("anticlockwise")
        elif event == RotaryEncoder.BUTTONDOWN:
            self.emit(SIGNAL("gpio_rotary_button_pressed"))
        elif event == RotaryEncoder.BUTTONUP:
            self.emit(SIGNAL("gpio_rotary_button_released"))
        return

    def reset_gpios(self):
        self.initReady = False
        self.worker = None   # free worker for garbage collection
        GPIO.cleanup()

    def startup_temperature_sensing(self):
        time.sleep(20)
        while True:
            humidity, temperature = Adafruit_DHT.read_retry(tempsensor, GPIO_TEMP)

            if humidity is not None and temperature is not None:
                print('Temp={0:0.1f}*C  Humidity={1:0.1f}%'.format(temperature, humidity))
                self.emit(SIGNAL("gpio_temperature"), temperature, humidity)
                time.sleep(delay_tempmeasurement)
            else:
                print 'Failed to get reading. Try again!'
                time.sleep(10)    # try it in 10 seconds again...

    def set_output_HIGH(self, pin):
        self.initReady = False
        # setting initReady temporary to false, is just to protect the switches ... not to catch any EMV
        if int(pin) in pins_in_use:
            if pins_in_use[int(pin)][0] == GPIO.OUT:
                logger.info("Channel: {0}, switching high".format(pin))
                GPIO.output(int(pin), 1)
                self.initReady = True
                return True
        self.initReady = True
        return False

    def set_output_LOW(self, pin):
        self.initReady = False
        # setting initReady temporary to false, is just to protect the switches ... not to catch any EMV
        if int(pin) in pins_in_use:
            if pins_in_use[int(pin)][0] == GPIO.OUT:
                logger.info("Channel: {0}, switching low".format(pin))
                GPIO.output(int(pin), 0)
                self.initReady = True
                return True
        self.initReady = True
        return False




class RotaryEncoder:

    CLOCKWISE=1
    ANTICLOCKWISE=2
    BUTTONDOWN=3
    BUTTONUP=4
    rotary_a = 0
    rotary_b = 0
    rotary_c = 0
    last_state = 0
    direction = 0
    # Initialise rotary encoder object
    def __init__(self,pinA,pinB,button,callback, parent):
        self.pinA = pinA
        self.pinB = pinB
        self.button = button
        self.callback = callback
        self.parent = parent
        if self.pinA is not None and self.pinB is not None:
            GPIO.setmode(GPIO.BOARD)

            GPIO.setwarnings(False)
            GPIO.setup(self.pinA, GPIO.IN)
            GPIO.setup(self.pinB, GPIO.IN)
            GPIO.add_event_detect(self.pinA, GPIO.FALLING,
            callback=self.switch_event)
            GPIO.add_event_detect(self.pinB, GPIO.FALLING,
            callback=self.switch_event)

        if self.button is not None:
            GPIO.setup(self.button, GPIO.IN)
            GPIO.add_event_detect(self.button, GPIO.BOTH,
            callback=self.button_event, bouncetime=200)

        return
        # Call back routine called by switch events
    def switch_event(self,switch):
        if not self.parent.initReady:
            print("ignoring because init is not ready")
            return
        if GPIO.input(self.pinA):
            self.rotary_a = 1
        else:
            self.rotary_a = 0
        if GPIO.input(self.pinB):
            self.rotary_b = 1
        else:
            self.rotary_b = 0

        self.rotary_c = self.rotary_a ^ self.rotary_b
        new_state = self.rotary_a * 4 + self.rotary_b * 2 + self.rotary_c * 1
        delta = (new_state - self.last_state) % 4
        self.last_state = new_state
        event = 0
        if delta == 1:
            if self.direction == self.CLOCKWISE:
                # print "Clockwise"
                event = self.direction
            else:
                self.direction = self.CLOCKWISE
        elif delta == 3:
            if self.direction == self.ANTICLOCKWISE:
                # print "Anticlockwise"
                event = self.direction
            else:
                self.direction = self.ANTICLOCKWISE
        if event > 0:
            self.callback(event)
        return
        # Push button event
    def button_event(self,button):
        if GPIO.input(button):
            event = self.BUTTONUP
        else:
            event = self.BUTTONDOWN
        self.callback(event)
        return
        # Get a switch state
    def getSwitchState(self, switch):
        return GPIO.input(switch)

# End of RotaryEncoder class

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

class MainWindow(QWidget):

    def __init__(self, parent=None):

        super(MainWindow, self).__init__(parent)
        self.layout_window = QHBoxLayout()
        if PIN_A is not None:
            self.rotary = QDial()
            self.rotary.setRange(0,100)
            self.rotary.setValue(50)
            self.rotary.setStyleSheet('''QDial
                                    {
                                        background-color: gray;
                                    }
                                    ''')
            self.layout_window.addWidget(self.rotary)

        self.buttons = []
        for btn in pins_in_use:
            button = QPushButton(("%d" % btn))
            button.setCheckable(True)
            self.buttons.append(button)
            self.layout_window.addWidget(button)

        self.setLayout(self.layout_window)
        self.setFocus(Qt.NoFocusReason)
        self.gpio_watchdog = Gpio_Watchdog()

        self.connect(self.gpio_watchdog, SIGNAL('gpio_button_pressed'), self.signalreader_buttons_on)  # carry pin no.
        self.connect(self.gpio_watchdog, SIGNAL('gpio_button_released'), self.signalreader_buttons_off)  # carry pin no.
        self.connect(self.gpio_watchdog, SIGNAL("gpio_rotary_turned"), self.signalreader_rotary) # carry direction
        self.connect(self.gpio_watchdog, SIGNAL("gpio_rotary_button_pressed"), self.signalreader_rotary_btn_pressed)
        self.connect(self.gpio_watchdog, SIGNAL("gpio_rotary_button_released"), self.signalreader_rotary_btn_released)

    def signalreader_buttons_on(self, channel):
        print("Pin {0} active".format(channel))
        for button in self.buttons:
            if int(button.text()) == channel:
                if not button.isChecked():
                    button.setChecked(True)
                else:
                    button.setChecked(False)

    def signalreader_buttons_off(self, channel):
        print("Pin {0} inactive".format(channel))
        for button in self.buttons:
            if int(button.text()) == channel:
                if not button.isChecked():
                    button.setChecked(False)
                else:
                    button.setChecked(True)

    def signalreader_rotary(self, direction):
        if direction is "clockwise":
            newRotary_value = self.rotary.value() +1
            if newRotary_value > 100: newRotary_value = 100
            self.rotary.setValue(newRotary_value)
        elif direction is "anticlockwise":
            newRotary_value = self.rotary.value() -1
            if newRotary_value < 0: newRotary_value = 0
            self.rotary.setValue(newRotary_value)

    def signalreader_rotary_btn_pressed(self):
        self.rotary.setStyleSheet('''QDial
                                    {
                                        background-color: yellow;
                                    }
                                    ''')

    def signalreader_rotary_btn_released(self):
        self.rotary.setStyleSheet('''QDial
                                    {
                                        background-color: gray;
                                    }
                                    ''')

    def closeEvent(self, QCloseEvent):
        print("Cleanup GPIOs")
        self.gpio_watchdog.reset_gpios()
        QCloseEvent.accept()


if __name__ == "__main__":
    from PyQt4.QtGui import *

    app = QApplication([])
    window = MainWindow()
    window.show()

    app.exec_()






