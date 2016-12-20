#!/usr/bin/env python
# -*- coding: utf8 -*-
# Parse output of BEG API and generate warnings if Trains are late.
# This is a very tailored output for my own needs. Feel free to fork and modify for your requirements
#
# data used from http://www.bayern-fahrplan.de/m5/de/
# WORK IN PROGRESS. This is not yet working
#
# The MIT License (MIT)
#
# Copyright (c) 2016 Andreas Sieferlinger

import requests
from requests.adapters import HTTPAdapter
import pprint
import datetime
import json
import time
import sys
import logging

# set up the logger
logger = logging.getLogger('bayernfahrplan')
logger.setLevel(logging.INFO)

# output logs to stderr
ch = logging.StreamHandler()
ch.setLevel(logging.WARNING)
logger.addHandler(ch)

BASE_URL = 'http://www.bayern-fahrplan.de/jqm/beg_lite'

LOCATION_ROSENHEIM = 80000821
LOCATION_MUNICH_EAST = 91000005
LOCATION_MUNICH_MAIN = 91000100

def fetch_departure_data(locationid, loadFromFile=None):
    urlparams = {
        "convertStopsPTKernel2LocationServer": 1,
        "itOptionsActive": 1,
        "limit": 40,
        "locationServerActive": 1,
        "mode": "direct",
        "name_dm": locationid, # ID of location we are searching things for
        "ptOptionsActive": 1,
        "stateless": 1,
        "type_dm": "any",
        "useAllStops": 1,
        "useRealtime": 1,
        "coordOutputFormat": "MRCV",
        "canChangeMOT": 0,
        "depType": "stopEvents",
        "includeCompleteStopSeq": 1,
        "mergeDep": 1,
        "nIPL": 1,
        "language": "de",
        "imparedOptionsActive": 1,
        "includedMeans": 1,
        "inclMOT_0": 1,
        "inclMOT_1": 1,
        "inclMOT_2": 1,
        "inclMOT_3": 1,
        "inclMOT_4": 1,
        "inclMOT_5": 1,
        "inclMOT_6": 1,
        "inclMOT_7": 1,
        "inclMOT_8": 1,
        "inclMOT_9": 1,
        "inclMOT_10": 1,
        "inclMOT_11": 1,
        "inclMOT_12": 1,
        "inclMOT_13": 1,
        "inclMOT_14": 1,
        "inclMOT_15": 1,
        "inclMOT_16": 1,
        "inclMOT_17": 1,
        "_": int(time.time()),
    }
    # url = "http://www.bayern-fahrplan.de/jqm/beg_lite/XML_DM_REQUEST?convertStopsPTKernel2LocationServer=1&itOptionsActive=1&limit=40&locationServerActive=1&mode=direct&name_dm=80000821&ptOptionsActive=1&stateless=1&type_dm=any&useAllStops=1&useRealtime=1&coordOutputFormat=MRCV&canChangeMOT=0&depType=stopEvents&includeCompleteStopSeq=1&mergeDep=1&nIPL=1&language=de&imparedOptionsActive=1&includedMeans=1&inclMOT_0=1&inclMOT_1=1&inclMOT_2=1&inclMOT_3=1&inclMOT_4=1&inclMOT_5=1&inclMOT_6=1&inclMOT_7=1&inclMOT_8=1&inclMOT_9=1&inclMOT_10=1&inclMOT_11=1&inclMOT_12=1&inclMOT_13=1&inclMOT_14=1&inclMOT_15=1&inclMOT_16=1&inclMOT_17=1&_=1482177011491"

    # get a requests session and configure some settings
    s = requests.Session()
    s.mount(BASE_URL, HTTPAdapter(max_retries=3))

    # fetch the data
    r = s.get('%s/XML_DM_REQUEST' % BASE_URL, params=urlparams, timeout=5)
    if r.status_code != requests.codes.ok:  # pylint: disable=E1101
        sys.exit(1)
    data = r.json()

    if loadFromFile is not None:
        logger.info('loading data from file')
        with open('request.json') as data_file:
            data = json.load(data_file, 'utf8')

    return data

class BFDeparture(object):
    def __init__(self, data):
        self._load(data)

                # if self.train_type in ['Meridian', 'EuroCity', 'EC', 'IC']:
                #     print self.delay, self.code, self.depart_time, self.train_type, self.number, self.destination, self.platform

    def _load(self, data):
        self.coords = data['coords']
        self.depart_time = datetime.datetime.strptime("%s:%s" % (data['dateTime']['date'], data['dateTime']['time']), "%d.%m.%Y:%H:%M")
        self.depart_from = data['name']
        self.next_stops = []
        for stop in data['nextStops']:
            splitted = stop.split(';')
            if len(splitted) >=1:
                try:
                    self.next_stops.append(splitted[1])
                except IndexError:
                    continue
                except UnicodeEncodeError:
                    print splitted
                    raise

        self.mode = data['mode']

        self.train_type = data['mode']['name']
        self.destination = data['mode']['destination']
        self.number = data['mode']['number']
        self.network = data['mode']['diva']['network']
        try:
            self.platform = data['ref']['platform'].replace('(', '').replace(')', '')
        except KeyError:
            self.platform = None

        self.code = data['mode']['code']
        try:
            self.delay = int(data['mode']['delay'])
        except KeyError:
            self.delay = None

    def interesting_train_type(self):
        if self.train_type in ['Meridian', 'EuroCity', 'EC', 'IC']:
            return True
        else:
            return False

    def stops_at(self, stop_name):
        if stop_name in self.destination:
            return True

        for stop in self.next_stops:
            if stop_name in stop:
                return True

        return False



departure_data = fetch_departure_data(LOCATION_MUNICH_EAST)
for departure in departure_data['departures']:
    #print pprint.pprint(departure)
    d = BFDeparture(departure)
    if d.stops_at(u'Rosenheim') and d.interesting_train_type():
        print d.delay, d.code, d.depart_time, d.train_type, d.number, d.destination, d.platform
