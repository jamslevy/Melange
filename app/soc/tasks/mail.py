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

"""Tasks related to Mail Dispatcher. """

__authors__ = [
  '"James Levy" <jamesalexanderlevy@gmail.com>',
  ]

import logging

from django import http

from google.appengine.api import mail
from google.appengine.api import memcache
from google.appengine.api.labs import taskqueue

from soc.tasks.helper import error_handler

def getDjangoURLPatterns():
  """Returns the URL patterns for the tasks in this module.
  """

  patterns = [(
      r'tasks/mail/sendmail$',
      'soc.tasks.mail.sendMail')]

  return patterns


def sendMail(request, *args, **kwargs):
  """Sends out an email using context to supply the needed information.

  Args:
    memcache_key (via request.POST):
        memcache key used to fetch context for the email message 

  Raises:
    Error that corresponds with the first problem it finds if the message
    is not properly initialized.

    List of all possible errors:
      http://code.google.com/appengine/docs/mail/exceptions.html
  """
  memcache_key = request.POST.get('memcache_key')
  # fetch context from the memcache
  context = memcache.get(memcache_key, namespace='mail')
  if not context:
    # since key isn't available, do not retry the task
    return error_handler.logErrorAndReturnOK(
    'unable to fetch mail params using memcache key %s' % memcache_key)
  # construct the EmailMessage from the given context
  message = mail.EmailMessage(**context)
  message.check_initialized()

  try:
    # send the message
    message.send()
    logging.info('sent mail with context %s' % context)
  except mail.Error, exception:
    logging.info(context)
    logging.exception(exception)
    # do not return HttpResponse - this will prompt a retry of the task
    return
  finally:
    # delete context from the memcache - and if delete call fails, continue
    try: 
      memcache.delete(memcache_key, namespace='mail')
    except: 
      pass
    return http.HttpResponse()
 