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
  def addToFeed(self, entity, update_type):
    """Sends out a message if there is only one unread notification.
    """
    # debugging
    import logging
    logging.info(entity)
    logging.info(update_type)
    new_feed_item = soc.models.newsfeed.FeedItem( 
    entity=entity,      # .should this just be key or key_name?
    update_type = update_type,
    scope_path = entity.scope_path)
    db.put(new_feed_item)  
    logging.info('just saved feed item %s' % new_feed_item.__dict__ ) 
    

  def retrieveFeed(self, entity, count=10):
    """ Retrieves feed for a given entity 
    """
    # argh old method wasn't working at all...
    # let's start from scratch.
    
    # use django time translation 
    return [{'name': "Entity Name", 
            'update_type': "deleted",
            "relative_time": "three minutes ago" }]
    
    
        


logic = Logic()
