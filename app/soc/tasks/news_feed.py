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
import time
import urllib

from django import http

from google.appengine.api import urlfetch
from google.appengine.api.labs import taskqueue
from google.appengine.ext import db

from soc.logic import accounts
from soc.logic import mail_dispatcher
import soc.logic.helper.notifications
import soc.logic.models as model_logic
from soc.logic.models.news_feed import logic as news_feed_logic
from soc.logic.models.subscriptions import logic as subscriptions_logic
from soc.logic.models.user import logic as user_logic
import soc.models.news_feed
import soc.models.linkable 
from soc.tasks.helper import error_handler
from soc.views.helper.news_feed import NewsFeed, news_feed


TASK_FEED_URL = 'tasks/news_feed/addtofeed'
HUB_URL = 'http://pubsubhubbub.appspot.com/'

def getDjangoURLPatterns():
  """Returns the URL patterns for the tasks in this module.
  """

  patterns = [(
      r'tasks/news_feed/addtofeed$',
      'soc.tasks.news_feed.AddToFeedTask')]

  return patterns
  
def scheduleAddToFeedTask(sender, receivers, update_type, **kwargs):
  """ Create new feed items for an event, using the Task API

  Params:
    sender - the entity sending the event
    receivers - a list of receivers receiving items in their feed
                for this event
    update_type - create, update, delete, etc.
  """
  #create unique feed_item_key for this item, in case task repeats
  feed_item_key = sender.key().id_or_name() + str(time.time())
  # optional payload message for this item 
  payload = kwargs.get('payload', None)
    
  task_params = {
      'feed_item_key' : feed_item_key,
      'payload': payload,
      'receivers': [receiver.key() for receiver in receivers],
      'sender_key': sender.key(),
      'update_type': update_type
      }
  
  user = user_logic.getForCurrentAccount()  
  if user:
    task_params['user_key'] = user.key().name()
  task = taskqueue.Task(params=task_params, url="/" + TASK_FEED_URL)
  task.add()



def AddToFeedTask(request, *args, **kwargs):
  """ Creates a FeedItem entity pairing an event for a sender entity
  and one receiver entity
  
  Params:
    feed_item_key - key_name used for feed item 
    sender_key - key for the entity sending the event
    receivers - entities assigned to get item in their feed
    update_type - create, update, delete, etc.
    payload - optional payload message for this feed item
    user_key - key_name of user who made the update 
  """
  params = request.POST
  """
  if not params.get('user_key'):
    return error_handler.logErrorAndReturnOK(
        'no user specified for AddToFeedTask')
  """
  feed_item_key = params.get('feed_item_key')
  user_key = params.get('user_key', None)
  if user_key:
    acting_user = user_logic.getFromKeyName(user_key)
  else:
    acting_user = None
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
  feed_item_properties = dict( 
  sender= db.Key(sender_key),
  receivers = receivers,
  update_type = update_type
  )
  
  if payload: 
    feed_item_properties['payload'] = payload

  if acting_user: 
    feed_item_properties['user'] = acting_user
    
  new_feed_item = news_feed_logic.updateOrCreateFromKeyName(
  feed_item_properties, feed_item_key)


  sender = db.get(sender_key)
  sendFeedItemEmailNotifications(sender, acting_user,
                                 update_type, payload, **kwargs)

  # send update ping for each receiver's feed
  receiver_entities = db.get(receivers)
  for receiver in receiver_entities:
    sendHubNotification(receiver)                  
  # task completed, return OK
  return http.HttpResponse('OK')


def sendHubNotification(receiver):
  """
  Sends PubSubHubbub Ping to Third-Party Hub
  
  TODO (james): Since this method may be called multiple times, is there 
  a way to batch the URLfetches for more efficiency?
  
  Params:
         receiver - the receiver entity with a newly updated feed
  """
  news_feed = NewsFeed(receiver)
  # resolve the URL of the entity's ATOM feed
  entity_feed_url = news_feed.getFeedUrl()
  headers = {'content-type': 'application/x-www-form-urlencoded'}
  post_params = {
    'hub.mode': 'publish',
    'hub.url': entity_feed_url,
  }
  payload = urllib.urlencode(post_params)
  try:
    # can these be sent in a batch?
    response = urlfetch.fetch(HUB_URL, method='POST', payload=payload)
  except urlfetch.Error:
    logging.exception('Failed to deliver publishing message to %s', HUB_URL)
  else:
    logging.info('URL fetch status_code=%d, content="%s"',
                 response.status_code, response.content)
                   
def sendFeedItemEmailNotifications(entity, acting_user, update_type, 
  payload,  context = {}, **kwargs):
  """
   Sends e-mail notification to user about new feed item. 
   Private payload info can be included in this message
   (while it is not included in the Atom feed)
  
  Params:
         entity - entity being updated
         acting_user - use who performed feed action (or None)
         update_type - type of update (created, updated, deleted)
         payload - extra information for message
         context - template dict
         
  """  


  if acting_user: 
    sender_name = acting_user.name
    sender = acting_user
  else:
    sender_name, sender  = mail_dispatcher.getDefaultMailSender()
  if getattr(entity, 'title', None):
    entity_title = entity.title
  else: 
    entity_title  = entity.key().name()
  
  subject = "%s - %s (%s) has been %s" % (
  os.environ['APPLICATION_ID'].capitalize(),
  entity_title, entity.kind(), update_type)
  
    
  # this should be a user query function and there should be
  # an access check for the receiver and then a check against a 
  # no_subscribe ListProperty for user for both sender and recevier.
  to_users = subscriptions_logic.getSubscribedUsersForFeedItem(entity)
  logging.info(to_users)
  # get site name
  site_entity = model_logic.site.logic.getSingleton()
  site_name = site_entity.site_name
   
  for to_user in to_users:
    messageProperties = {
        # message configuration
        'to_name': to_user.name,
        'to': accounts.denormalizeAccount(to_user.account).email(),  
        'sender_name': sender_name,
        'sender': accounts.denormalizeAccount(sender.account).email(),
        # feed item info
        'acting_user': acting_user,
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

      
