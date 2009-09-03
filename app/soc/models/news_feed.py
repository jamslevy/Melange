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
  """ A feed item referencing a sender entity (the updated entity)
  and a receiver entity (where the feed item should appear)
  
  If an entity has multiple receievers, a FeedItem entity is created
  for each receiver-sender pair, so that there are often several
  FeedItem entities created for a single update. 
  
  """
  # refers to the entity this feed item is about
  sender = db.ReferenceProperty(reference_class=None,
               required=True)
  # refers to scope of feed where this item will appear 
  #receiver_key = db.StringProperty(required=True)
  receivers = db.ListProperty(db.Key)
  
  user = db.ReferenceProperty(reference_class=soc.models.user.User,
                                collection_name="feed_items",
                                required=False)
                                
  # type of update
  update_type = db.StringProperty(required=True, choices=
                  ['created', 'updated', 'deleted', 'commented on'])  
  
  # a message or markup that go along with the feed item
  payload = db.TextProperty(required=False)

  #: date when the feed item was created
  created = db.DateTimeProperty(auto_now_add=True)

