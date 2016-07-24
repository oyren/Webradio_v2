#!/usr/bin/env python
# -*- coding: utf-8 -*-
################################  WARNING: This script have to be executed as ROOT to work like expected ##############
# Monitor the mounting-status of a given folder (defined below)
# If the mounting-status changes, signals were emitted
# SIGNAL("sig_usb_connected"))    if usb device was recently connected
# SIGNAL("sig_usb_disconnected")) if usb device was recently disconnected
# if umount is used, you have to run this script as ROOT (sudo is used)
# mounting status can be called as a single request to .ismounted() which returnes True or False
#######################################################################################################################

import os
import commands
import time
from PyQt4.QtCore import QObject, SIGNAL, QThread
import logging

logger = logging.getLogger("webradio")

interval = 1  #in sec.

class USB_manager(QObject):

    def __init__(self, folder_to_be_monitored, parent=None):
        QObject.__init__(self, parent)

        self.worker = None
        self.mountingFolder = folder_to_be_monitored

    def umount(self):
        if os.geteuid() == 0:   # also check if script was started as root-user
            res = commands.getoutput("sudo umount {0}".format(self.mountingFolder))

            if res == "":   # if umount was sucessfull, no failuremessage is raised
                logger.info("Unmounting was succesfull...")
                return True
            else:           # if there was any kind of returned text ... it was a failure-message
                logger.warning("Can not unmount {0}, because of : {1}".format(self.mountingFolder, res))
                return False
        else:
            logger.error("Umounting is only allowed for root-users, please start this script as root using sudo")
            return False

    def ismounted(self):
        logger.info("USB-Manager: Check if USB-Stick is mounted...")
        print(os.path.ismount(self.mountingFolder))
        return os.path.ismount(self.mountingFolder)


    def isrunning(self):
        return True if self.worker is not None else False

    def startup_notifier(self):

        self.worker = WorkerThread(self.__observe_usbMounting)
        self.worker.start()

    def stop_notifier(self):

        if self.worker is not None:
            self.worker.terminate()                              #terminating a runnig QThread is DANGEROUS ....
            self.worker = None

    def __observe_usbMounting(self):

        last_mounting_state = None

        while True:
            try:
                current_mounting_state = os.path.ismount(self.mountingFolder)
            except:
                current_mounting_state = None

            if last_mounting_state is not None:
                if current_mounting_state == False and last_mounting_state == True:
                    logger.info("USB is disconnected")
                    self.emit(SIGNAL("sig_usb_disconnected"))
                elif current_mounting_state == True and last_mounting_state == False:
                    logger.info("USB is connected")
                    self.emit(SIGNAL("sig_usb_connected"))
            else:
                if current_mounting_state == True:
                    logger.info("USB is initially connected")
                    self.emit(SIGNAL("sig_usb_connected"))
                elif current_mounting_state == False:
                    logger.info("USB is initially disconnected")
                    self.emit(SIGNAL("sig_usb_disconnected"))

            last_mounting_state = current_mounting_state

            time.sleep(interval)


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
    mediadevice = USB_manager()
    state = mediadevice.ismounted()
    if state == True:
        logger.info("Initially the USB Device is mounted")
    else:
        logger.info("Initially the USB Device is NOT mounted")

    logger.info("Starting Notifier now.")
    mediadevice.startup_notifier()
    time.sleep(20)
    logger.info("unmounting now")
    res = mediadevice.umount()
    if res == True:
        logger.info("Operation sucessfull")
    else:
        logger.info("Operation failed")
    time.sleep(5)




