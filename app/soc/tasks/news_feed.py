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

from soc.logic import accounts
import soc.logic.models as model_logic
from soc.logic.models.user import logic as user_logic
import soc.logic.helper.notifications
import soc.models.news_feed
import soc.models.linkable 
from soc.tasks.helper import error_handler
from soc.views.helper.news_feed import NewsFeed as NewsFeedHelper

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
  params:
  
    sender - the entity sending the event
    receivers - a list of receivers receiving items in their feed
                for this event
    update_type - create, update, delete, etc.
  """
  
  user = user_logic.getForCurrentAccount()
  # optional payload message for this item 
  payload = kwargs.get('payload', None)
    
  task_params = {
      'payload': payload,
      'receiver_keys': [receiver.key() for receiver in receivers],
      'sender_key': sender.key(),
      'update_type': update_type,
      'user_key': user.key().name()
      }
    
  task = taskqueue.Task(params=task_params, url="/" + TASK_FEED_URL)
  task.add()



def AddToFeedTask(request, *args, **kwargs):
  """ Creates a FeedItem entity pairing an event for a sender entity
  and one receiver entity
  
  params:
    sender_key - key for the entity sending the event
    receiver_key - one receiver receiving item in their feed
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
  receiver_keys = params.get('receiver_keys', '').split(',')
  if not receiver_keys:
    return error_handler.logErrorAndReturnOK(
        'no receiver_keys specified for AddToFeedTask')

  update_type = params.get('update_type')
  if not update_type:
    return error_handler.logErrorAndReturnOK(
        'no update_type specified for AddToFeedTask')  
        
  # optional params
  payload = params.get('payload')
  
  # save items to datastore
  save_items = []
  for receiver_key in receiver_keys:
    new_feed_item = soc.models.news_feed.FeedItem( 
    sender_key= str(sender_key), #TODO(james): db.Key
    receiver_key = str(receiver_key),
    user = user,
    update_type = update_type
    )
    
    if payload: 
      new_feed_item.payload = payload
      
    save_items.append(new_feed_item)
  db.put(save_items)
  
  sendFeedItemEmailNotifications(user, sender_key, 
                 receiver_keys, update_type, payload, **kwargs)
                  
  # task completed, return OK
  return http.HttpResponse('OK')

from soc.logic import mail_dispatcher


# this belongs in notifications module
def sendFeedItemEmailNotifications(user, sender_key, receiver_keys, 
    update_type, payload, context = {}, from_user = False, **kwargs):
  """
   Sends e-mail notification to user about new feed item. 
   Private payload info can be included in this message
   (while it is not included in the Atom feed)
   
  """  

   # no from_user required
  sender = db.get(sender_key)
  feed_helper = NewsFeedHelper(sender)
  if from_user: 
    sender_name, sender  = from_user.name, from_user
  else:
    sender_name, sender  = mail_dispatcher.getDefaultMailSender()
  for receiver_key in receiver_keys:
    receiver = db.get(receiver_key)
    if getattr(receiver, 'title', None):
      receiever_title = receiver.title
    else: receiver_title  = receiver.key().name()
    subject = "%s (%s) has been %s" % (
    receiver_title, receiver.kind(), update_type)
    
    # this should be a user query function and there should be
    # an access check for the receiver and then a check against a 
    # no_subscribe ListProperty for user for both sender and recevier.
    to_users = getSubscribedUsersForFeedItem(receiver, sender)

    # get site name
    site_entity = model_logic.site.logic.getSingleton()
    site_name = site_entity.site_name
     
    for to_user in to_users:
      messageProperties = {
          'to_name': to_user.name,
          'sender_name': sender_name,
          'to': accounts.denormalizeAccount(to_user.account).email(),
          'sender': sender,
          'payload': payload,
          'subject': subject,
          'payload': payload,
          'url': feed_helper.linkToEntity(),
          'site_location': 'http://%s' % os.environ['HTTP_HOST'],
          }
      # send out the message using the news_feed template
      mail_dispatcher.sendMailFromTemplate(
      'soc/mail/news_feed_notification.html', messageProperties)

      
# this should be replaced in user_logic   
def getSubscribedUsersForFeedItem(receiver, sender):
  user = user_logic.getForCurrentAccount()
  print ""
  logging.info(user)
  return [user]
  


 
