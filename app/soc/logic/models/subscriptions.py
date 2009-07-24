#!/usr/bin/python2.5
#
# Copyright 2009 the Melange authors.
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

"""Subscriptions (Model) query functions. """

__authors__ = [
  '"James Levy" <jamesalexanderlevy@gmail.com>',
  ]

import logging

from google.appengine.ext import db

from soc.logic.models import base
import soc.logic.models as model_logic
from soc.logic.models.user import logic as user_logic
import soc.models.subscriptions 



class Logic(base.Logic):
  """Logic methods for the Subscriptions model.
  """

  def __init__(self, model=soc.models.subscriptions.Subscriptions,
              scope_logic=user_logic):
    """Defines the name, key_name and model for this entity.
    """

    super(Logic, self).__init__(model, scope_logic=scope_logic)


    
  def createSubscriber(self, user, has_email_subscription=True):
    """
    creates news feed subscriber for user (added to onCreate hook)
    """
    subscriber = soc.models.subscriptions.Subscriptions(
    user = user,
    has_email_subscription = has_email_subscription)
    db.put(subscriber)
    
    
  def getSubscribedUsersForFeedItem(self, entity):
    """ retrieve all users who have an active role for 
    the receiever entity, and then check to make sure they haven't
    set the no_subscribe preference to block either the sender or 
    receieverkind, (or the sender or receiver entities?)
    
    TODO(james): use Checker.checkHasActiveRole -
    how would this be made as universal as possible for any model kind?
    
    """
    #
    # get all users who have active read-access for this entity. 
    #
    #
    #
    return [i.user for i in soc.models.subscriptions.Subscriptions.all(
    ).filter('subscriptions', entity)] 
    """
    subscribed_users = []
    for user in access_passed_users(entity):
      subscriber = user.feed_subscriber.get()
      if subscriber and subscriber.has_email_subscription:
         if entity.key() not in subscriber.unsubscribed:
           subscribed_users.append(user) # what if entity scope is unsubscribed?
    return subscribed_users
    """

logic = Logic()
