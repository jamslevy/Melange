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

"""This module contains the Newsfeed Model."""

__authors__ = [
  'JamesLevy" <jamesalexanderlevy@gmail.com>',
]

from google.appengine.ext import db
from soc.models import base
import soc.models.linkable 
import soc.models.user

class FeedItem(base.ModelWithFieldAttributes):
  """ An item referencing an entity and its scope. 
  """

  # refers to the entity this feed item is about 
  sender_key = db.StringProperty(required=False)
  # refers to scope of feed where this item will appear 
  receiver_key = db.StringProperty(required=False)
  
  user = db.ReferenceProperty(reference_class=soc.models.user.User,
                                collection_name="feed_items",
                                required=False)
                                
  update_type = db.StringProperty(required=False)

  #scope = db.ReferenceProperty(soc.models.linkable.Linkable,
  #required=True, collection_name='receieved_feed_items')
  #entity = db.ReferenceProperty(soc.models.linkable.Linkable,
  #required=False, collection_name='sent_feed_items')

  update_type = db.StringProperty(required=True)
  # link to sender page
  link = db.StringProperty(required=True)
  
  
  # a message or markup that go along with the feed item
  payload = db.TextProperty(required=False)

  #: date when the feed item was created
  created = db.DateTimeProperty(auto_now_add=True)
  #: date when the feed item was created (is it ever modified?) 
  modified = db.DateTimeProperty(auto_now=True)  
  # story, payload?
  
  def sender(self):
    return db.get(self.sender_key)

  def receiver(self):
    print "BLAH"
    return db.get(self.receiver_key)
    
