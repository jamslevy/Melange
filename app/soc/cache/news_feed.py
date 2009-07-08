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

TODO(James): As SRabbelier notes, this code is too similar to 
the other cache modules and these can likely be refactored to share
the same code.

"""

__authors__ = [
  'JamesLevy" <jamesalexanderlevy@gmail.com>',
  ]

import logging

from google.appengine.api import memcache

import soc.cache.base
from soc.logic import accounts

def key(func):
  """Returns the memcache key for the news_feed.
  """
  entity = func.entity
  return 'news_feed_for_%s_%s' % (entity.kind(), entity.key().id_or_name())


def get(entity, *args, **kwargs):
  """Retrieves the news_feed for the specified entity from the memcache.
  """
  # only cache the page for non-logged-in users
  if accounts.getCurrentAccount(normalize=False):
    return (None, None)
  if not entity:
    return (None, None)
  memcache_key = key(entity)
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
  memcache.add(memcache_key, result, retention)


def flush(entity):
  """Removes the news_feed for the entity from the memcache.

  Also calls soc.cache.rights.flush for the specified user.

  Args:
    id: defaults to the current account if not set
  """
  memcache_key = key(entity)
  memcache.delete(memcache_key)

# define the cache function
cache = soc.cache.base.getCacher(get, put)
