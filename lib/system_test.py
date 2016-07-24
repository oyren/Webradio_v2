#!/usr/bin/env python
# -*- coding: utf-8 -*-

import urllib2

INTERNET = 'http://www.google.com'
RADIODE = 'http://radio.de'
LASTFM = 'http://www.lastfm.de'
WEATHERCOM = 'http://wxdata.weather.com/'

def test_onlineServices():
    service_internet = False
    service_radiode = False
    service_lastfm = False
    service_weathercom = False

    result = {"internet" : False,
              "radiode" : False,
              "lastfm" : False,
              "weathercom" : False}

    try:                                                                    # check internet-connection
        urllib2.urlopen(INTERNET,timeout=1)
        service_internet = True
    except urllib2.URLError:                                                # if there is an error
        print("Internet:", service_internet)
        print("Aborting")
        return False, result

    if service_internet:
        try:                                                                    # check internet-connection
            urllib2.urlopen(RADIODE,timeout=1)
            service_radiode = True
        except urllib2.URLError:                                                # if there is an error
            service_radiode = False

        try:                                                                    # check internet-connection
            urllib2.urlopen(LASTFM,timeout=1)
            service_lastfm = True
        except urllib2.URLError:                                                # if there is an error
            service_lastfm = False

        try:                                                                    # check internet-connection
            urllib2.urlopen(WEATHERCOM,timeout=1)
            service_weathercom = True
        except urllib2.URLError:                                                # if there is an error
            service_weathercom = False

    print("Internet:   ", service_internet)
    print("Radio.de:   ", service_radiode)
    print("lastfm.de:  ", service_lastfm)
    print("weather.com:", service_weathercom)

    result.update({"internet" : service_internet})
    result.update({"radiode" : service_radiode})
    result.update({"lastfm" : service_lastfm})
    result.update({"weathercom" : service_weathercom})


    if service_radiode and service_lastfm and service_weathercom:
        return True, result
    else:
        return False, result

def test_serverconnection():
    pass

def test_usbconnection():
    pass



if __name__ == "__main__":
    print("Check Online-Services...")
    status, results = test_onlineServices()

    if status:
        print("All Tests passed")
    else:
        print("At least one of the system-tests failed !")
        for key, value in results.iteritems():
            if not value:
                print("Please Debug:")
                print(key)




