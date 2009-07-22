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
import soc.tasks.news_feed

class Logic():
  """Logic methods for the Newsfeed.
  """


  def addToFeed(self, sender, receivers, update_type, **kwargs):
    # see method for doc string
    return soc.tasks.news_feed.scheduleAddToFeedTask(sender, receivers, 
    update_type, **kwargs)

        
  def retrieveFeed(self, entity, count=10, sort_order="-receiver_key"):
    """ Retrieves feed for a given entity 
    """
    feed_items = soc.models.news_feed.FeedItem.all().filter(
    "receiver_key =", str(entity.key())).order(sort_order).fetch(count)
    return feed_items
    
  def createSubscriber(self, user, has_email_subscription=True):
    subscriber = soc.models.news_feed.NewsFeedSubscriber(
    user = user,
    has_email_subscription = has_email_subscription)
    db.put(subscriber)
    
    
    
    
    
"""

from soc.logic.models.news_feed import logic as newsfeed_logic
from soc.models.user import User
users = User.all().fetch(1000)
for user in users:
 newsfeed_logic.createSubscriber(user)
 
"""
    
logic = Logic()


