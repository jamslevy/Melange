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

"""Module contains news_feed memcaching functions.
"""

__authors__ = [
  'JamesLevy" <jamesalexanderlevy@gmail.com>',
  ]


import logging

from google.appengine.api import memcache

from soc.logic import accounts

import soc.cache.base


def key(entity):
  """Returns the memcache key for the news_feed.
  """

  return 'news_feed_for_%s_%s' % (entity.kind(), entity.key().id_or_name())


def get(self, *args, **kwargs):
  """Retrieves the news_feed for the specified user from the memcache.
  """

  # only cache the page for non-logged-in users
  # TODO: figure out how to cache everything but the news_feed 
  # also, no need to normalize as we don't use it anyway
  if accounts.getCurrentAccount(normalize=False):
    return (None, None)

  entity = self._logic.getFromKeyFields(kwargs)

  # if we can't retrieve the entity, leave it to the actual method
  if not entity:
    return (None, None)

  memcache_key = key(entity)
  logging.info("Retrieving %s" % memcache_key)
  # pylint: disable-msg=E1101
  return memcache.get(memcache_key), memcache_key

def put(result, memcache_key, *args, **kwargs):
  """Sets the news_feed  for the specified user in the memcache.

  Args:
    news_feed: the news_feed to be cached
  """

  # no sense in storing anything if we won't query it later on
  # also, no need to normalize as we don't use it anyway
  if accounts.getCurrentAccount(normalize=False):
    return

  # Store news_feed for just ten minutes to force a refresh every so often
  retention = 10*60

  logging.info("Setting %s" % memcache_key)
  # pylint: disable-msg=E1101
  memcache.add(memcache_key, result, retention)


def flush(entity):
  """Removes the news_feed for the current user from the memcache.

  Also calls soc.cache.rights.flush for the specified user.

  Args:
    id: defaults to the current account if not set
  """

  memcache_key = key(entity)
  logging.info("Flushing %s" % memcache_key)
  # pylint: disable-msg=E1101
  memcache.delete(memcache_key)


# define the cache function
cache = soc.cache.base.getCacher(get, put)
