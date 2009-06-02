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
import soc.model.newsfeed


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
    import logging
    logging.info(entity)
    logging.info(update_type)
    if not entity.scope: 
      logging.info("NO SCOPE")
      return 
    new_feed_item = soc.model.newsfeed.FeedItem( 
    entity=entity,      # .should this just be key or key_name?
    update_type = update_type,
    scope = entity.scope) 
    
    


logic = Logic()
