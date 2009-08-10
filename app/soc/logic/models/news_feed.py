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
  '"JamesLevy" <jamesalexanderlevy@gmail.com>',
  ]

import logging

from google.appengine.ext import db

from soc.logic.models import base
import soc.models.news_feed
import soc.models.linkable 


class Logic(base.Logic):
  """Logic methods for the Newsfeed.
  """

  def __init__(self, model=soc.models.news_feed.FeedItem):
    """Defines the name, key_name and model for this entity.
    """

    super(Logic, self).__init__(model)


  def addToFeed(self, sender, receivers, update_type, **kwargs):
    # see method for doc string
    import soc.tasks.news_feed
    return soc.tasks.news_feed.scheduleAddToFeedTask(sender, receivers, 
    update_type, **kwargs)

        
  def retrieveFeed(self, entity, count=10, sort_order="-created"):
    """ Retrieves feed for a given entity 
    
    Params:
      entity - entity rendering its news feed
      count - number of feed items to retrieve
      sort_order - sorting method 
      
    """
    feed_items = soc.models.news_feed.FeedItem.all(
    ).filter('receivers', entity
    ).order(sort_order
    ).fetch(count)
    return feed_items

    

    
logic = Logic()


