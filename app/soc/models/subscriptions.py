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

"""This module contains the Subscriptions Model."""

__authors__ = [
  'JamesLevy" <jamesalexanderlevy@gmail.com>',
]

from google.appengine.ext import db

import soc.models.user

class Subscriber(db.Model):
  """ Manages subscriptions for user
  """
  user = db.ReferenceProperty(reference_class=soc.models.user.User,
                                collection_name="subscriber",
                                required=True)
  # universal toggle
  has_email_subscription = db.BooleanProperty(required=True, default=True)
  # list of entities to which user is subscribed
  subscriptions = db.ListProperty(db.Key)
  
  
  
