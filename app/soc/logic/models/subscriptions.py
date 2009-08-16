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

  def __init__(self, model=soc.models.subscriptions.Subscriber,
              scope_logic=user_logic):
    """Defines the name, key_name and model for this entity.
    """

    super(Logic, self).__init__(model, scope_logic=scope_logic)


  def createSubscriber(self, user, has_email_subscription=False):
    """ creates news feed subscriber for user (added to onCreate hook)
    
    Args:
        user - user parent of subscriber
        has_email_subscription - toggle on email subscription for user
    """
    # check if there already is a subscriber for this user
    subscriber = self.getFromKeyName(self.getSubscriberKeyName(
    user.key().name()))
    if subscriber: return subscriber
    # if none exists, create new subscriber
    subscriber = soc.models.subscriptions.Subscriber(
    key_name = self.getSubscriberKeyName(user.key().name()),
    user = user,
    has_email_subscription = has_email_subscription)
    # save subscriber entity
    db.put(subscriber)
    return subscriber
    

  def getSubscriberKeyName(self, user_key_name):
    """ standardized key name format 
    
    Args:
         user_key_name - key name of user
    """
    return "subscriber_" + user_key_name


  def getSubscriberForUser(self, user):
    """ standardized key name format 
    Args:
     user - user parent of subscriber
    """
    subscriber = user.subscriber.get()
    if not subscriber:
      subscriber = self.createSubscriber(user)
    return subscriber
    
  def isSubscribed(self, user, entity):
    """ return Bool indicating if user is subscribed to an entity
    
    Args:
         user - user to check 
         entity - subscription entity 
    """
    if not user: return
    subscriber = self.getSubscriberForUser(user)
    return (entity.key() in subscriber.subscriptions)
    
  def editSubscription(self, user, is_subscribed):
    """ Through the Edit Profile page, a user
    can toggle a global e-mail subscription setting. Subscribe-by-star 
    UI controls subscription to individual entities) 
    
    Args:
        user - user updating their global subscription preference 
    """
    subscriber = self.getSubscriberForUser(user)
    subscriber.has_email_subscription = is_subscribed
    db.put(subscriber)
          
  def editEntitySubscription(self, entity_key, subscribe):
    """ Edit subscription for a single entity
    
    Args:
      entity_key - key of subscription entity
      subscribe - Boolean describing current subscribe status
    """
    entity_key = db.Key(entity_key)
    user = self._scope_logic.getForCurrentAccount() 
    subscriber = self.getSubscriberForUser(user)
    if subscribe and entity_key not in subscriber.subscriptions:
      subscriber.subscriptions.append(entity_key)
      logging.info('added subscription for entity_key %s for user %s'
      % (entity_key, user.key().name()))
    elif not subscribe and entity_key in subscriber.subscriptions:
      subscriber.subscriptions.remove(entity_key)
      logging.info('removed subscription for entity_key %s for user %s'
      % (entity_key, user.key().name()))
    else: return
    db.put(subscriber)

  def getSubscribedUsersForFeedItem(self, entity):
    """ retrieve all users who are subscribed to the sender entity
    of a new FeedItem
    Args:
        entity - feed item entity
    """
    return [i.user for i in soc.models.subscriptions.Subscriber.all(
    ).filter('subscriptions', entity)] 


  def updateSubscribersForEntity(self, entity):
    """ Automated method to add subscription to all users with 
    an active role for this entity 
    
    Args:
         entity - entity subject of subscription
    """
    update_method = getattr(update_logic, entity.kind().lower(), None)
    if update_method:
      users = update_method(entity)
      update_logic.addEntitySubscriptionForUsers(users, entity)
    # in case no update method is found
    else: 
      logging.error('no subscriber update method found for entity kind\
      %s' % entity.kind().lower())
      return None


class UpdateLogic():
  """ 
  Update the subscribers for an entity
  
  """

  def addEntitySubscriptionForUsers(self, users, entity):
    """ 
    add a new subscription for users for a given entity.
    
    Args:
         users - list of users
         entity - subscription entity
    """
    subscribers = [ logic.getSubscriberForUser(user) for user in users ]
    for subscriber in subscribers:
      if entity.key() not in subscriber.subscriptions:
        subscriber.subscriptions.append(entity.key())
    db.put(subscribers)

  """ 
  
  Model-specific methods 
  
  TODO (James): 
  
  The access view helper module could be very useful,
  but is deeply integrated with the workflow of checking a single 
  user within the context of an entity's view. 
  
  The only option appears to be creating new logic infrastructure,
  but leveraging any existing logic would surely be better. 
  
  """        
      
  def document(self, entity):
    users = []#user_logic.getForFields({})
    return users

  def survey(self, entity):
    users = []#user_logic.getForFields({})
    return users

  def studentproject(self, entity):
    users = []#user_logic.getForFields({})
    return users
            
    
logic = Logic()
update_logic = UpdateLogic()


