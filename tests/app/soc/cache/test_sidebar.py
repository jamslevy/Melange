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


__authors__ = [
  '"Sverre Rabbelier" <sverre@rabbelier.nl>',
  ]


from google.appengine.api import users
from google.appengine.api import memcache

import unittest

from soc.cache import sidebar


class SidebarCacheTest(unittest.TestCase):
  """Tests that the sidebar properly uses caching
  """

  def setUp(self):
    self.called = 0
    self.user = users.get_current_user()

  def tearDown(self):
    memcache.flush_all()

  def testGetCurrentUser(self):
    """Santiy check to see if get_current_user returns same value
    """

    self.assertEqual(self.user, users.get_current_user())

  def testKey(self):
    """Test that the key method returns a unique key
    """

    self.assertEqual("sidebar_for_users.User(email='test@example.com')",
                     sidebar.key(self.user))

  def testGet(self):
    """Test that get without setting something returns None
    """
    self.assertEqual(None, sidebar.get())

  def testGetPut(self):
    """Test that getting after putting gives back what you put in
    """

    sidebar.put(42)
    self.assertEqual(42, sidebar.get())

  def testFlush(self):
    """Test that getting after putting and flushing returns None
    """

    sidebar.put(42)
    sidebar.flush()
    self.assertEqual(None, sidebar.get())

  def testCache(self):
    """Test that the result of a cached sidebar is cached
    """

    @sidebar.cache
    def getAnswer():
      self.called = self.called + 1
      return 42

    self.assertEqual(42, getAnswer())
    self.assertEqual(42, getAnswer())
    self.assertEqual(self.called, 1)

