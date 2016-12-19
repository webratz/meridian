#!/usr/bin/env python
# -*- coding: utf8 -*-
# Parse output of BEG API and generate warnings if Trains are late.
# WORK IN PROGRESS. This is not yet working
#
# The MIT License (MIT)
#
# Copyright (c) 2016 Andreas Sieferlinger

import requests
import pprint
import datetime
import json

url = "http://www.bayern-fahrplan.de/jqm/beg_lite/XML_DM_REQUEST?convertStopsPTKernel2LocationServer=1&itOptionsActive=1&limit=40&locationServerActive=1&mode=direct&name_dm=80000821&ptOptionsActive=1&stateless=1&type_dm=any&useAllStops=1&useRealtime=1&coordOutputFormat=MRCV&canChangeMOT=0&depType=stopEvents&includeCompleteStopSeq=1&mergeDep=1&nIPL=1&language=de&imparedOptionsActive=1&includedMeans=1&inclMOT_0=1&inclMOT_1=1&inclMOT_2=1&inclMOT_3=1&inclMOT_4=1&inclMOT_5=1&inclMOT_6=1&inclMOT_7=1&inclMOT_8=1&inclMOT_9=1&inclMOT_10=1&inclMOT_11=1&inclMOT_12=1&inclMOT_13=1&inclMOT_14=1&inclMOT_15=1&inclMOT_16=1&inclMOT_17=1&_=1482177011491"
r = requests.get(url)

data = r.json()

# with open('request.json') as data_file:
#     data = json.load(data_file, 'utf8')

class BFDeparture(object):
    def __init__(self, data):
        self._load(data)

        if self.train_type in ['Meridian', 'EuroCity', 'EC', 'IC']:
            print self.depart_time, self.train_type, self.number, self.destination, self.delay, self.code, self.platform
            for i in self.next_stops:
                print i

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


for departure in data['departures']:
    #print pprint.pprint(departure)
    BFDeparture(departure)
