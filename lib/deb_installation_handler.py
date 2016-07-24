#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys, getpass
import subprocess as sp

def isPackageInstalled(packagename):
    '''
    Args:
        programmname: Package-Name of the Programm which you want to check.
    Returns: True / False if the programm or package was installed on the requested system or not.
    '''
    if __systemCall("dpkg-query -W -f='${"+"Status"+"} \
    ${"+"Version"+"}\n'"+" {0} 2> /dev/null".format(packagename)).startswith("install ok"):
        return True
    else:
        return False

def installPackages(passwrd, packagenames=[]):
    '''
    echo -e $PASSWD | sudo -S <command>
    '''
    if len(packagenames) > 0 and passwrd != "":
        packagelist = ""
        for package in packagenames:
            packagelist += package + " "  #add each package seperated only with a space
        __systemCall("echo -e '{0}' | sudo -S apt-get -y install {1}".format(passwrd, packagelist))

def __systemCall(command):
    return_value = sp.Popen(command, shell=True, stdout=sp.PIPE).stdout.read()
    return return_value


if __name__ == "__main__":
    print(isPackageInstalled("python-mpd"))
    print(isPackageInstalled("supertuxkart"))
    installPackages("test")
    sys.exit(0) # return 0 (Process successful)
