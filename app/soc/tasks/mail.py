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
import os

from google.appengine.api import mail
from google.appengine.api.labs import taskqueue
from google.appengine.ext import db

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
    context : The context supplied to the email message (dictionary)

  Raises:
    Error that corresponds with the first problem it finds iff the message
    is not properly initialized.

    List of all possible errors:
      http://code.google.com/appengine/docs/mail/exceptions.html
  """
  context = request.POST
  # construct the EmailMessage from the given context
  message = mail.EmailMessage(**context)
  message.check_initialized()

  try:
    # send the message
    message.send()
  except mail.Error, exception:
    logging.info(context)
    logging.exception(exception)
    