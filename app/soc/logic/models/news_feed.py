#!/usr/bin/python2.5
#
# Copyright 2008 the Melange authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Newsfeed (Model) query functions.
"""

__authors__ = [
  'JamesLevy" <jamesalexanderlevy@gmail.com>',
  ]

import logging
from google.appengine.ext import db
import soc.models.news_feed
import soc.models.linkable 
from soc.logic.models.user import logic as user_logic


# custom url names
# value should correlate to params['url_name'] in view
# Regex sub() method could also be used to add the underscores.
CUSTOM_URL_NAMES = { 
'studentproject': 'student_project',
'prioritygroup': 'priority_group',
'studentproposal':'student_proposal', 
'groupapp':'group_app', 
'orgapp':'org_app', 
'clubmember':'club_member', 
'organization': 'org'
}
      
      
class Logic():
  """Logic methods for the Newsfeed.
  """

  def __init__(self):
    """ initiate logic module
    """
    pass


  def addToFeed(self, sender, receivers, update_type, payload=None):
    """ Adds new item to feed for sender, given a list of receievers 
    """

    from google.appengine.api.labs import taskqueue
    taskqueue.add(url='/addToFeedTask', params={})

    save_items = []
    user = user_logic.getForCurrentAccount()
    for receiver in receivers:
      if not receiver: 
         logging.warning('empty receiver sent for newsfeed item')
         continue
         
        
      
      
      url_name = CUSTOM_URL_NAMES.get(sender.kind().lower())
      if not url_name: url_name = sender.kind().lower()
      
      new_feed_item = soc.models.news_feed.FeedItem( 
      sender_key= str(sender.key()),      # .should this just be key or key_name?
      receiver_key = str(receiver.key()),
      user = user,
      update_type = update_type,
      link = "/%s/show/%s" % (url_name, sender.key().name() ) 
      )
      if payload: new_feed_item.payload = payload
      save_items.append(new_feed_item)
    db.put(save_items)  
    

  def addToFeedTask(self):
    """TaskQueue method to add item to newsfeed
    """
    pass


  def retrieveFeed(self, entity, count=10):
    """ Retrieves feed for a given entity 
    """
    # argh old method wasn't working at all...
    # let's start from scratch.
    
    # use django time translation 
    
    feed_items = soc.models.news_feed.FeedItem.all().filter(
    "receiver_key =", str(entity.key())).fetch(1000)
    return feed_items[:count]
    
    
        


logic = Logic()
