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
import hashlib
import pickle
import os
import toml
from pushbullet import Pushbullet

CONFDIR = os.environ['HOME'] + "/.meridian"

if not os.path.exists(CONFDIR):
    os.makedirs(CONFDIR)

with open(CONFDIR + "/meridian.toml") as conffile:
    config = toml.loads(conffile.read())

# set up the logger
logger = logging.getLogger('bayernfahrplan')
logger.setLevel(logging.DEBUG)

# output logs to stderr
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
logger.addHandler(ch)

BASE_URL = 'http://www.bayern-fahrplan.de/jqm/beg_lite'

LOCATION_ROSENHEIM = 80000821
LOCATION_MUNICH_EAST = 91000005
LOCATION_MUNICH_MAIN = 91000100

def fetch_departure_data(locationid, loadFromFile=None):
    """
    construct URL and fetch the data we will work on later
    """
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
        "MOT" : 0,
        "_": int(time.time()),
    }
    # url = "http://www.bayern-fahrplan.de/jqm/beg_lite/XML_DM_REQUEST?convertStopsPTKernel2LocationServer=1&itOptionsActive=1&limit=40&locationServerActive=1&mode=direct&name_dm=80000821&ptOptionsActive=1&stateless=1&type_dm=any&useAllStops=1&useRealtime=1&coordOutputFormat=MRCV&canChangeMOT=0&depType=stopEvents&includeCompleteStopSeq=1&mergeDep=1&nIPL=1&language=de&imparedOptionsActive=1&includedMeans=1&inclMOT_0=1&inclMOT_1=1&inclMOT_2=1&inclMOT_3=1&inclMOT_4=1&inclMOT_5=1&inclMOT_6=1&inclMOT_7=1&inclMOT_8=1&inclMOT_9=1&inclMOT_10=1&inclMOT_11=1&inclMOT_12=1&inclMOT_13=1&inclMOT_14=1&inclMOT_15=1&inclMOT_16=1&inclMOT_17=1&_=1482177011491"

    # get a requests session and configure some settings
    s = requests.Session()
    s.mount(BASE_URL, HTTPAdapter(max_retries=3))

    # fetch the data
    r = s.get('%s/XML_DM_REQUEST' % BASE_URL, params=urlparams, timeout=5)
    if r.status_code != requests.codes.ok:  # pylint: disable=E1101
        logger.error("Could not fetch data via HTTP")
        sys.exit(1)
    data = r.json()

    # for development purposes we can also read from a json file
    if loadFromFile is not None:
        logger.info('loading data from file')
        with open('request.json') as data_file:
            data = json.load(data_file, 'utf8')

    return data

def get_or_none(data, key):
    # we can only work on dicts
    if not isinstance(data, dict):
        return None
    try:
        d = data[key]
    except KeyError:
        d = None

    return d

class BFNote(object):
    """
    Object to handle notes in a nicer way and add some convenience functions
    """
    def __init__(self, data):
        self._load(data)

    def _load(self, data):
        self.appearance = get_or_none(data, 'appearance')
        self.header = get_or_none(data, 'header')
        self.priority = get_or_none(data, 'priority')
        self.text = get_or_none(data, 'text')

        self.alltext = ""
        textlist = []
        if self.header is not None:
            textlist.append(self.header)
        if self.text is not None:
            textlist.append(self.text)

        if len(textlist) >=1:
            for i in textlist:
                self.alltext += i


    def normal_prio(self):
        """
        does the note have a "normal" priority?
        """
        if self.priority is not None:
            if 'veryLow' in self.priority:
                return False
            return True

        return False


class BFDeparture(object):
    """
    object holding all information for a departure
    its created from the json data we fetch from BEG
    """
    def __init__(self, data):
        self.id = None
        self._load(data)

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

        self.notes = []
        if data['notes'] is not None:
            for i in data['notes']:
                self.notes.append(BFNote(i))

        # note texts
        self.notetexts = []
        for note in self.notes:
            if note.normal_prio():
                self.notetexts.append(note.alltext)

        self._compute_id()

    def _compute_id(self):
        """
        calculcate an hash over the text
        id changes with every content change, so that we send an renotification
        """
        hashstr = "%s %s %s %s" % (self.number, self.depart_time, self.notetexts, self.delay)
        did = hashlib.sha256(str(hashstr)).hexdigest()
        self.id = did
        return did


    def shall_we_notifiy(self):
        if self.delay >= 5:
            return True
        if len(self.notetexts) > 0:
            return True

        return False


    def interesting_train_type(self):
        """
        we are only interested in a few "products" / "train types", so let's just work on them
        """
        if self.train_type in ['Meridian', 'EuroCity', 'EC', 'IC', 'InterCity']:
            return True
        else:
            return False

    def stops_at(self, stop_name):
        """
        Find out if this train stops at the give location name
        """
        if stop_name in self.destination:
            return True

        for stop in self.next_stops:
            if stop_name in stop:
                return True

        return False

    def pushbullet(self):
        """
        send a notification to a push bullet channel
        """
        # intialize PushBullet API
        pb = Pushbullet(config['pushbullet']['api_key'])

        # print d.delay, d.depart_time, d.number, d.destination, d.platform, d.notetexts
        text = u""" %s nach %s von %s
Abfahrt: %s
Verspätung: %s Minuten
Hinweise:
%s

        """ % (self.number, self.destination, self.platform, self.depart_time, self.delay, '\n'.join(self.notetexts))
        headline = u"%s nach %s" % (self.number, self.destination)


        for channel in pb.channels:
            if config['pushbullet']['delaychannel'] in channel.name:
                channel.push_note(headline, text)
        return text








def run():
    """
    actually glue everything together and run
    """
    departure_data = fetch_departure_data(LOCATION_ROSENHEIM, loadFromFile=None)

    # load a file to check what we already have notified
    try:
        already_notified = pickle.load(open(CONFDIR + "/beg_notify_store.bin", "rb"))
    except IOError:
        logger.warning('Could not load already_notified list. Starting with an empty list')
        already_notified = []

    for departure in departure_data['departures']:
        #print pprint.pprint(departure)
        d = BFDeparture(departure)
        if d.id not in already_notified:
            if d.stops_at(u'München') and d.interesting_train_type():
                print d.delay, d.depart_time, d.number, d.destination, d.platform, ' '.join(d.notetexts)
                if d.shall_we_notifiy():
                    print d.delay, d.depart_time, d.number, d.destination, d.platform, ' '.join(d.notetexts)
                    d.pushbullet()
            already_notified.append(d.id)

    # store the list of notified items back to disk
    try:
        pickle.dump(already_notified, open(CONFDIR + "/beg_notify_store.bin", "wb"))
    except IOError as e:
        logger.warning('Could not save already_notified list %s', e)

run()
