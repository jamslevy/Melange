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


from google.appengine.ext import db
import soc.models.news_feed
import soc.models.linkable 

class Logic():
  """Logic methods for the Newsfeed.
  """

  def __init__(self):
    """
    """

  # this should be a background task
  def addToFeed(self, sender, receivers, update_type, payload=None):
    """Sends out a message if there is only one unread notification.
    """

    # debugging
    import logging
    save_items = []
    for receiver in receivers:
      
      logging.info('saving feed item for sender %s and receiver %s' % 
      (sender.key().name(), receiver.key().name() ) )
      new_feed_item = soc.models.news_feed.FeedItem( 
      sender_key= str(sender.key()),      # .should this just be key or key_name?
      receiver_key = str(receiver.key()),
      update_type = update_type )
      if payload: new_feed_item.payload = payload
      save_items.append(new_feed_item)
    
    logging.info('saved %d feed items for sender %s' % ( 
    len(save_items), sender.key().name() ) ) 
    db.put(save_items)  
    
    

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
