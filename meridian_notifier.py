#!/usr/bin/env python3
# -*- coding: utf8 -*-
#
# This script scrapes the HTML of an website to generate notifications if something new is there
#
# The MIT License (MIT)
#
# Copyright (c) 2016 Andreas Sieferlinger

import requests
import sys
import os
import logging
from logging import handlers
import hashlib
from pushbullet import Pushbullet
import pickle
import toml
import twitter
import pprint
import iso8601
import socket

# work around warnings in older python 2.7 versions
logging.captureWarnings(True)

CONFDIR = os.environ['HOME'] + "/.meridian"
if not os.path.exists(CONFDIR):
    os.makedirs(CONFDIR)

with open(CONFDIR + "/meridian.toml") as conffile:
    config = toml.loads(conffile.read())

# set up the logger
logger = logging.getLogger('meridian')
logger.setLevel(logging.INFO)

# output logs to stderr
ch = logging.StreamHandler()
ch.setLevel(logging.WARNING)
logger.addHandler(ch)

# mail errors to my owner
mailh = handlers.SMTPHandler(config['maillogger']['mailhost'],
                             config['maillogger']['fromaddr'],
                             config['maillogger']['toaddr'],
                             'Meridian Maillogger Error')
mailh.setLevel(logging.ERROR)
logger.addHandler(mailh)


class MeridianInterruption(object):
    """
    Abstract object of an Interruption
    """
    def __init__(self, headline, content, start, end, category, mid):
        self.headline = headline
        self.content = content
        self.start = start
        self.end = end
        self.category = category
        self.id = self.compute_id()
        self.mid = mid  # Meridian ID

    def compute_id(self):
        """
        calculcate an hash over the text
        id changes with every content change, so that we send and renotification
        """
        return hashlib.sha256(self.content.encode('utf-8')).hexdigest()

    def pushbullet(self):
        """
        send a notification to a push bullet channel
        """
        # intialize PushBullet API
        pb = Pushbullet(config['pushbullet']['api_key'])

        text = """%s bis %s

%s

Kategorie: %s
Links:
        """ % (self.start, self.end, self.content, self.category)

        for channel in pb.channels:
            if config['pushbullet']['channel'] in channel.name:
                channel.push_note(self.headline, text)
        return text

    def twitter(self):
        twapi = twitter.Api(
            consumer_key=config['twitter']['consumer_key'],
            consumer_secret=config['twitter']['consumer_secret'],
            access_token_key=config['twitter']['access_token_key'],
            access_token_secret=config['twitter']['access_token_secret'],
            input_encoding='utf8')

        message = "%s: %s - %s" % (self.category, self.headline,
                                   MERIDIAN_INTERRUPTION_URL)
        try:
            logger.info("sent twitter message for id %s", self.id)
            twapi.PostUpdates(status=message)
        except Exception as e:
            logger.error("Could not post twitter message for id %s %s",
                         self.id, e)


# scrape the hell out of the website
class MeridianInterruptionPage(object):
    def __init__(self,
                 url='http://www.meridian-bob-brb.de/de/baustellen.json'):
        self.url = url
        self.interruptions = []
        self.data = self.get_data()
        self.parse_data()

    def get_data(self):
        """
        get json
        """
        try:
            r = requests.get(self.url)
            if r.status_code == requests.codes.ok:  # pylint: disable=E1101
                return r.json()
            else:
                raise requests.exceptions.HTTPError()

        except requests.exceptions.RequestException as e:
            logger.error('Could not load the the json')
            logger.error(e)
            sys.exit(1)

    def parse_data(self):
        for element in self.data.get('current'):  # TODO: add also upcoming
            headline = element['title']
            content = element['body']
            category = element['category']
            start = iso8601.parse_date(element['starts_at'])
            try:
                end = iso8601.parse_date(element['ends_at'])
            except iso8601.iso8601.ParseError:
                end = None
            mid = element['id']
            if 1 in element['line_ids']:
                # print element['id'], headline
                self.interruptions.append(
                    MeridianInterruption(headline, content, start, end,
                                         category, mid))


def run():
    """
    actually glue everything together and run
    """
    try:
        mip = MeridianInterruptionPage()
    except (requests.exceptions.HTTPError, socket.timeout):
        # print('could not fetch data')
        sys.exit(1)

    # load a file to check what we already have notified
    try:
        already_notified = pickle.load(
            open(CONFDIR + "/notify_store.bin", "rb"))
    except IOError:
        logger.warning(
            'Could not load already_notified list. Starting with an empty list'
        )
        already_notified = []

    for i in mip.interruptions:
        if i.id not in already_notified:
            # send notifications
            i.pushbullet()
            #i.twitter()
            logger.info('Sent notification for id %s', i.id)
            already_notified.append(i.id)
        logger.info('NOT sending a notification for id %s', i.id)

    # store the list of notified itmes back to disk
    try:
        pickle.dump(already_notified, open(CONFDIR + "/notify_store.bin",
                                           "wb"))
    except IOError:
        logger.warning('Could not save already_notified list')


run()

m = MeridianInterruptionPage()
