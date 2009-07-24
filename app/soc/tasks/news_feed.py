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

"""Tasks related to News Feed. """

__authors__ = [
  '"James Levy" <jamesalexanderlevy@gmail.com>',
  ]

import logging
import os

from django import http

from google.appengine.api.labs import taskqueue
from google.appengine.ext import db

import soc.logic.helper.notifications
import soc.logic.models as model_logic
from soc.logic.models.subscriptions import logic as subscriptions_logic
from soc.logic.models.user import logic as user_logic
import soc.models.news_feed
import soc.models.linkable 
from soc.tasks.helper import error_handler
from soc.views.helper.news_feed import news_feed

TASK_FEED_URL = 'tasks/news_feed/addtofeed'

def getDjangoURLPatterns():
  """Returns the URL patterns for the tasks in this module.
  """

  patterns = [(
      r'tasks/news_feed/addtofeed$',
      'soc.tasks.news_feed.AddToFeedTask')]

  return patterns
  
def scheduleAddToFeedTask(sender, receivers, update_type, **kwargs):
  """ Create new feed items for an event, using the Task API
  Args:
  
    sender - the entity sending the event
    receivers - a list of receivers receiving items in their feed
                for this event
    update_type - create, update, delete, etc.
  """
  
  # optional payload message for this item 
  payload = kwargs.get('payload', None)
    
  task_params = {
      'payload': payload,
      'receivers': [receiver.key() for receiver in receivers],
      'sender_key': sender.key(),
      'update_type': update_type,
      }
  
  user = user_logic.getForCurrentAccount()  
  if user:
    task_params['user_key'] = user.key().name()
  task = taskqueue.Task(params=task_params, url="/" + TASK_FEED_URL)
  task.add()



def AddToFeedTask(request, *args, **kwargs):
  """ Creates a FeedItem entity pairing an event for a sender entity
  and one receiver entity
  
  Args:
    sender_key - key for the entity sending the event
    receivers - entities assigned to get item in their feed
    update_type - create, update, delete, etc.
    payload - optional payload message for this feed item
  """
  params = request.POST
  if not params.get('user_key'):
    return error_handler.logErrorAndReturnOK(
        'no user specified for AddToFeedTask')
  user = user_logic._model.get_by_key_name(params.get('user_key'))
  sender_key = params.get('sender_key')
  if not sender_key:
    return error_handler.logErrorAndReturnOK(
        'no sender_key specified for AddToFeedTask')  
  receivers = [db.Key(key) for key in params.get(
               'receivers', '').split(',')]
  if not receivers:
    return error_handler.logErrorAndReturnOK(
        'no receivers specified for AddToFeedTask')

  update_type = params.get('update_type')
  if not update_type:
    return error_handler.logErrorAndReturnOK(
        'no update_type specified for AddToFeedTask')  
        
  # optional params
  payload = params.get('payload')
  
  # save item to datastore
  new_feed_item = soc.models.news_feed.FeedItem( 
  sender_key= str(sender_key), #TODO(james): db.Key
  receivers = receivers,
  user = user,
  update_type = update_type
  )
  
  if payload: 
    new_feed_item.payload = payload
    
  db.put(new_feed_item)
  
  sendFeedItemEmailNotifications(sender_key, user,
                                 update_type, payload, **kwargs)
                  
  # task completed, return OK
  return http.HttpResponse('OK')


from soc.logic import accounts
from soc.logic import mail_dispatcher
# this belongs in notifications module
def sendFeedItemEmailNotifications(entity_key, user, update_type, payload, 
    context = {}, **kwargs):
  """
   Sends e-mail notification to user about new feed item. 
   Private payload info can be included in this message
   (while it is not included in the Atom feed)
  
  Args:
         entity_key - entity being updated
         user - use who performed feed action
         update_type - type of update (created, updated, deleted)
         payload - extra information for message
         context - template dict
         
  """  

   # no from_user required
  entity = db.get(entity_key)
  if user: user_name = user.name
  else:
    user_name, user  = mail_dispatcher.getDefaultMailSender()
    
  if getattr(entity, 'title', None):
    entity_title = entity.title
  else: entity_title  = entity.key().name()
  subject = "%s (%s) has been %s" % (
  entity_title, entity.kind(), update_type)
  
  # this should be a user query function and there should be
  # an access check for the receiver and then a check against a 
  # no_subscribe ListProperty for user for both sender and recevier.
  to_users = subscriptions_logic.getSubscribedUsersForFeedItem(entity)

  # get site name
  site_entity = model_logic.site.logic.getSingleton()
  site_name = site_entity.site_name
   
  for to_user in to_users:
    messageProperties = {
        'to_name': to_user.name,
        'to': accounts.denormalizeAccount(to_user.account).email(),          
        'sender_name': user_name,
        'sender': accounts.denormalizeAccount(user.account).email(),
        'entity': entity,
        'payload': payload,
        'subject': subject,
        'url': news_feed.linkToEntity(entity),
        'site_location': 'http://%s' % os.environ['HTTP_HOST']
        }
    logging.info(messageProperties)
    # send out the message using the news_feed template
    mail_dispatcher.sendMailFromTemplate(
    'soc/mail/news_feed_notification.html', messageProperties)

      
