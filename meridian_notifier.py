#!/usr/bin/env python
# -*- coding: utf8 -*-
#
# This script scrapes the HTML of an website to generate notifications if something new is there
#
# The MIT License (MIT)
#
# Copyright (c) 2016 Andreas Sieferlinger

from bs4 import BeautifulSoup
import requests
from datetime import datetime
import sys
import logging
import hashlib
from pushbullet import Pushbullet
import pickle
import toml

with open("meridian.toml") as conffile:
    config = toml.loads(conffile.read())

# concact some variables
MERIDIAN_INTERRUPTION_URL = "%s%s%s" % (config['meridian']['base_url'], config['meridian']['interruption_url_suffix'], config['meridian']['line'])

# intialize PushBullet API
pb = Pushbullet(config['pushbullet']['api_key'])

# set up the logger
logger = logging.getLogger('meridian')
logger.setLevel(logging.INFO)

# otput logs to stderr
ch = logging.StreamHandler()
ch.setLevel(logging.WARNING)
logger.addHandler(ch)

class MeridianInterruption(object):
    """
    Abstract object of an Interruption
    """
    def __init__(self, headline, content, start, end, category, urls=None):
        self.headline = headline
        self.content = content
        self.start = start
        self.end = end
        self.category = category
        self.urls = urls
        self.id = self.compute_id()


    def compute_id(self):
        """
        calculcate an hash over the text
        id changes with every content change, so that we send and renotification
        """
        return hashlib.sha256(str(self.content)).hexdigest()

    def pushbullet(self):
        """
        send a notification to a push bullet channel
        """

        text = """%s bis %s

%s

Kategorie: %s
Links:
%s
        """ % (self.start, self.end, self.content.text, self.category, '\n'.join(self.urls))


        for channel in pb.channels:
            if config['pushbullet']['channel'] in channel.name:
                channel.push_note(self.headline, text)
        return text


# scrape the hell out of the website
class MeridianInterruptionPage(object):
    def __init__(self, url=MERIDIAN_INTERRUPTION_URL):
        self.url = url
        self.basehtml = None

        self.get_interruptions_base_html()
        self.interruptions = self.get_interruptions()

    def get_interruptions_base_html(self):
        """
        get the interesting html part of the website
        """
        try:
            r = requests.get(self.url)
            if r.status_code == requests.codes.ok: # pylint: disable=E1101
                soup = BeautifulSoup(r.text)
                basehtml = soup.findAll('ul', class_='mod-interruption-list')[0]
                self.basehtml = basehtml
                return basehtml
            else:
                return None
        except requests.exceptions.RequestException as e:
            logger.error('Could not parse the base html')
            logger.error(e)
            sys.exit(1)

    def parse_interruption_item(self, html):
        """
        try to get some useful data out of the html
        """
        try:
            category = html.find('div', class_='mod-interruption-list__header-title').text.strip('\n')
        except:
            logger.error('Could not parse the category')
            category = None

        try:
            timeframe = html.find('div', class_='mod-interruption-list__header-date').text
            if 'bis' in timeframe:
                startstring, endstring = timeframe.split('-')
                start = datetime.strptime(startstring.strip(), "%d.%m.%y ab %H:%M")
                end = datetime.strptime(endstring.strip(), "%d.%m.%y bis %H:%M")
            else:
                start = datetime.strptime(timeframe.strip(), "%d.%m.%y ab %H:%M")
                end = start

        except:
            logger.error('Could not parse the date of the interruption')
            start = None
            end = None

        try:
            headline = html.find('div', class_='mod-interruption-list__headline').text.strip()
        except:
            logger.error('Could not parse the headline')
            headline = None

        try:
            content = html.find('div', class_='mod-interription-list__description')
        except:
            logger.error('Could not parse the content of the interruption')
            content = None


        try:
            urls = []
            for i in html.findAll('a', class_='mod-download-list__link', href=True):
                urls.append("%s%s" % (config['meridian']['base_url'], i['href']))
        except:
            logger.info('Did not find any URLS')
            urls = []


        # create a new Interruption object
        interruption = MeridianInterruption(headline, content, start, end, category, urls)
        return interruption

    def get_interruptions(self):
        """
        get a lst of interruptions on the website
        """
        irupts = []
        for item in self.basehtml.findAll('li', class_='mod-interruption-list__item'):
            interruption = self.parse_interruption_item(item)
            irupts.append(interruption)
        return irupts


def run():
    """
    actually glue everything together and run
    """
    mip = MeridianInterruptionPage()

    # load a file to check what we already have notified
    try:
        already_notified = pickle.load(open("notify_store.bin", "rb"))
    except IOError:
        logger.warning('Could not load already_notified list. Starting with an empty list')
        already_notified = []


    for i in mip.interruptions:
        if i.id not in already_notified:
            i.pushbullet() # send notification
            logger.info('Sent notification for id %s', i.id)
            already_notified.append(i.id)

    # store the list of notified itmes back to disk
    try:
        pickle.dump(already_notified, open("notify_store.bin", "wb"))
    except IOError:
        logger.warning('Could not save already_notified list')

run()
