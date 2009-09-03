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

"""Notification (Model) query functions.
"""

__authors__ = [
  '"Lennard de Rijk" <ljvderijk@gmail.com>',
  '"JamesLevy" <jamesalexanderlevy@gmail.com>',
  ]


from google.appengine.ext import db

from soc.cache import sidebar
from soc.logic.helper import notifications
from soc.logic.models import base
from soc.logic.models import user as user_logic
from soc.logic.models.subscriptions import logic as subscription_logic
from soc.logic.models.news_feed import logic as newsfeed_logic

import soc.models.notification



class NewsFeedNotification():
  """
  
  Not based on Notification model because no special notification model
  is required.
  
  """
  
  def sendNotification(self, notification_msg, entity):
    """ Comment on an entity, sending e-mails and RSS updates
    via Newsfeed logic 
    
    Args:
        notification_msg - Text comment made for entity
        entity - entity being commented on 
    """
    # TODO: No generalized way to reliably get parent's parent 
    # without model-specific logic
    receivers = [entity.scope]
    subscription_logic.updateSubscribersForEntity(entity)
    newsfeed_logic.addToFeed(entity, receivers, "commented on", 
    payload=notification_msg)

     

class Logic(base.Logic):
  """Logic methods for the Notification model.
  """

  def __init__(self):
    """Defines the name, key_name and model for this entity.
    """
    super(Logic, self).__init__(model=soc.models.notification.Notification,
         base_model=None, scope_logic=user_logic)

  def _onCreate(self, entity):
    """Sends out a message if there is only one unread notification.
    """

    # create a special query on which we can call count
    query = db.Query(self._model)
    query.filter('scope =', entity.scope)
    query.filter('unread = ', True)

    # count the number of results with a maximum of two
    unread_count = query.count(2)

    if unread_count == 1:
      # there is only one unread notification so send out an email
      notifications.sendNewNotificationMessage(entity)

    sidebar.flush(entity.scope.account)
    super(Logic, self)._onCreate(entity)

  def _updateField(self, entity, entity_properties, name):
    """If unread changes we flush the sidebar cache.
    """

    value = entity_properties[name]

    if (name == 'unread') and (entity.unread != value):
      # in case that the unread value changes we flush the sidebar.
      sidebar.flush(entity.scope.account)

    return True


logic = Logic()
