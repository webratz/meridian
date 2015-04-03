#!/usr/bin/env python
 # -*- coding: utf8 -*-
# script to check webpages from TransDev companies (e.g. Meridian, BOB), and check for notifications
# sends an mail if there is something new
# quite hackish, but worked well during the big storm in april 2015
#
# debian / ubuntu dependencies: sudo apt-get install python-requests python-mailer python-bs4
#
# The MIT License (MIT)
#
# Copyright (c) 2015 Andreas Sieferlinger
# 

from bs4 import BeautifulSoup
import requests
from datetime import datetime, timedelta
from time import sleep
from mailer import Mailer
from mailer import Message

debug = True


class MeridianStrecke(object):
  def __init__(self):
    self.url                = 'http://www.der-meridian.de/strecken-fahrplaene/linie/1-munchen-hbf-rosenheim-salzburg-hbf'
    self.config_mail_from   = 'no-reply@configure.me'       # from mail address
    self.config_mail_to     = 'changeme'                    # desitnation mail address, use a list for multiple
    self.config_mail_server = 'use your smtp server'        # smtp mail server
    self.config_loop_sleep  = 5                             # minutes
    self.soup               = None
    self.incidents          = []
    self.construction       = []
    self.last_updated       = None  # current value
    
  def get_html(self):
    """
    try to get the html of the website
    """
    try:
      r = requests.get(self.url)
      if r.status_code == 200:
        soup = BeautifulSoup(r.text)
        self.soup = soup
        return soup
    except:
      if debug:
        raise
      return None
     

  def get_incidents(self):
    """
    parse the html for incidents
    """
    self.get_html()
    # find stoerung div
    data = self.soup.find('div', attrs={'class': 'stoerung'})
    
    if data == None:
        return None
  
    # get all lists
    uls = data.findAll('ul')

    # all list items
    lis = []
    for ul in uls:
      for li in ul.findAll('li'):
        if li.find('ul'):
          break
        lis.append(li)

    for li in lis:
      # full text incl headers
      # print li.text.encode("utf-8")
      
      ps = li.findAll('p')
      text = ""
      for p in ps:
        text = text + p.text.encode("utf-8").lstrip() + "\n "
      
      # get message title
      title = li.find('h4', attrs={'class': 'subline'}).text.encode("utf-8").strip()

      # get last updated timestamp
      updated_text = li.find('span', attrs={'class': 'updated'}).text.replace('\n', ' ').lstrip().rstrip()
      updated_ts = datetime.strptime(updated_text, "Meldung vom: %d.%m.%Y um %H:%M Uhr")
      self.last_updated = updated_ts
      
      self.incidents.append({'title' : title,
        'text' : text,
        'updated' : updated_ts})
      return self.incidents
    
  def need_notify(self):
    """
    check if we should send out an notification
    """
    for i in self.incidents:
      old = datetime.now() - timedelta(minutes=self.config_loop_sleep) # there may be cases where this is not matching
      if i['updated'] > old:
        self.send_notification(i)
      if debug:
        # always send a mail
        self.send_notification(i)

  def send_notification(self, data):
    """
    expects an icident dict
    """
    text = "Meldung: %s \nStand: %s\nQuelle: %s" % (data['text'], data['updated'], self.url) 
    message = Message(From    = self.config_mail_from,
                      To      = self.config_mail_to,
                      charset = "utf-8")
    message.Subject = "Störungsmeldung: %s" % data['title']
    message.Body    = text

    sender = Mailer(self.config_mail_server)
    sender.send(message)
    
def loop():
  # main loop
  while True:
    try:
      ms.get_incidents()
      ms.need_notify()
      # only check every X minutes
      if debug:
        print "check"
    except:
      if debug:
        raise
      pass
    
    sleep(ms.config_loop_sleep * 60)


# start and configure
ms = MeridianStrecke()
# config hints in class init
ms.url                = 'http://www.der-meridian.de/strecken-fahrplaene/linie/1-munchen-hbf-rosenheim-salzburg-hbf'
ms.config_mail_from   = ''
ms.config_mail_server = ''
ms.config_mail_to     = '' # use a list for multiple recipients

loop()
