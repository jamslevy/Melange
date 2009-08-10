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


__authors__ = [
  '"JamesLevy" <jamesalexanderlevy@gmail.com>',
  ]


import unittest

from google.appengine.api import users

from soc.models import news_feed
from soc.logic.models.document import logic as document_logic
from soc.logic.models.news_feed import logic as news_feed_logic
from soc.logic.models.site import logic as site_logic
from soc.logic.models.user import logic as user_logic


class FeedItemTest(unittest.TestCase):
  """Tests related to news_feed logic.
  """

  def setUp(self):
    """Set up required for sample feed item test. 
    
    Creates sender, receiver, and user entities required for news_feed
    test. 
    """

    # ensure that current user is created
    properties = {
        'account': users.get_current_user(),
        'link_id': 'current_user',
        'name': 'Current User',
        }

    key_name = user_logic.getKeyNameFromFields(properties)
    self.user = user_logic.updateOrCreateFromKeyName(properties, key_name)

    site_properties = {
      'key_name': 'site',
      'link_id': 'site',
      }

    key_name = site_logic.getKeyNameFromFields(site_properties)
    self.site = site_logic.updateOrCreateFromKeyName(
    site_properties, key_name)
        
    document_properties = {
      'key_name': 'site/site/home',
      'link_id': 'home',
      'scope_path': 'site',
      'scope': self.site,
      'prefix': 'site',
      'author': self.user,
      'title': 'Home Page',
      'short_name': 'Home',
      'content': 'This is the Home Page',
      'modified_by': self.user,
      }

    key_name = document_logic.getKeyNameFromFields(document_properties)
    self.document = document_logic.updateOrCreateFromKeyName(
    document_properties, key_name)

  def testDocumentFeedItem(self):
    """ Make sure that FeedItem was created for new document entity
    """

    document_feed = news_feed_logic.retrieveFeed(self.document)
    self.failIfEqual(document_feed, [])
    self.failUnlessEqual(document_feed[0].sender, self.document)
    self.failUnlessEqual(document_feed[0].receivers[0], self.site)
    self.failUnlessEqual(document_feed[0].user, self.user)
