#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt4.QtCore import *
from PyQt4.QtGui import *
import time
import global_vars
import logging

logger = logging.getLogger("webradio")

BUTTONS = []
for values in global_vars.configuration.get("GPIOS_IN").itervalues():
    try:
        BUTTONS.append(int(values))
    except:
        logger.error(u"Der GPIO_IN '{0}' ist ungültig!".format(values.decode("utf-8")))

try:
    delay_tempmeasurement = int(global_vars.configuration.get("DHT11").get("delay_tempmeasurement"))
except:
    delay_tempmeasurement = 180
    logger.error(u"Die Verzögerung (delay_tempmeasurement '{0}' ist ungültig!".format(values.decode("utf-8")))
    logger.info(u"Die Verzögerung (delay_tempmeasurement wurde auf 180 Sekunden gestellt (3 min.)")


class GPIO_Simulator(QWidget):

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)

        global_layout = QVBoxLayout()
        layout_tools = QHBoxLayout()
        self.buttons = []
        for item in BUTTONS:
            #print(item)
            button = QButton(("%d" % item),self.handleButtonPressed, self.handleButtonReleased, self)
            self.buttons.append(button)
            layout_tools.addWidget(button)

        self.rotary = QDial()
        self.rotary.setRange(0,100)
        self.rotary.setValue(50)
        self.rotary.valueChanged.connect(self.handleRotary)
        self.oldValue = 50
        layout_tools.addWidget(self.rotary)
        self.label = QLabel()
        self.label.setText("Idle")
        global_layout.addWidget(self.label)
        global_layout.addLayout(layout_tools)
        self.setLayout(global_layout)
        self.worker = WorkerThread(self.startup_temperature_sensing)
        self.worker.start()

        self.connect(self, SIGNAL('gpio_button_pressed'), self.signalreader_buttons_on)  # carry pin no.
        self.connect(self, SIGNAL('gpio_button_released'), self.signalreader_buttons_off)  # carry pin no.
        self.connect(self, SIGNAL("gpio_rotary_turned"), self.signalreader_rotary) # carry direction
        self.connect(self, SIGNAL("gpio_temperature"), self.signalreader_temp)

    def handleButtonPressed(self, item):
        #print("Button {0} pressed".format(item))
        self.emit(SIGNAL("gpio_button_pressed"), int(item))

    def handleButtonReleased(self, item):
        #print("Button {0} released".format(item))
        self.emit(SIGNAL("gpio_button_released"), int(item))

    def handleRotary(self, value):
        if value > self.oldValue:
            #print("Rotary turned right")
            self.emit(SIGNAL("gpio_rotary_turned"), "clockwise")
        else:
            self.emit(SIGNAL("gpio_rotary_turned"), "anticlockwise")
            #print("Rotary turned left")

        self.oldValue = value

    def signalreader_buttons_on(self, channel):
        self.label.setText("Pressed Button {0}".format(channel))

    def signalreader_buttons_off(self, channel):
        self.label.setText("Released Button {0}".format(channel))

    def signalreader_rotary(self, direction):
        self.label.setText("Rotary turned {0}".format(direction))

    def signalreader_temp(self, temp, hum):
        self.label.setText("Temp={0:0.1f}*C  Humidity={1:0.1f}%".format(int(temp), int(hum)))

    def startup_temperature_sensing(self):
        time.sleep(10)

        while True:

            humidity, temperature = "45", "25"

            if humidity is not None and temperature is not None:
                #print 'Temp={0:0.1f}*C  Humidity={1:0.1f}%'.format(int(temperature), int(humidity))
                self.emit(SIGNAL("gpio_temperature"), temperature, humidity)
                time.sleep(delay_tempmeasurement)
            else:
                #print 'Failed to get reading. Try again!'
                time.sleep(10)    # try it in 10 seconds again...

    def set_output_HIGH(self, pin):
        #print("Setting pin '{0}' to high").format(pin)
        return True

    def set_output_LOW(self, pin):
        #print("Setting pin '{0}' to low").format(pin)
        return True


class QButton(QPushButton):

    def __init__(self, name, callback_pressed, callback_released, parent=None):
        QPushButton.__init__(self,parent)

        self.name = name
        self.setText(name)
        self.callback_pressed = callback_pressed
        self.callback_released = callback_released
        self.pressed.connect(lambda : self.callback_pressed(self.name))
        self.released.connect(lambda : self.callback_released(self.name))


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
    from PyQt4.QtGui import *

    app = QApplication([])
    window = GPIO_Simulator()
    window.show()

    app.exec_()
