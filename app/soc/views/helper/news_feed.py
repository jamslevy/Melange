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

"""Newsfeed (Model) view helper functions.
"""

__authors__ = [
  'JamesLevy" <jamesalexanderlevy@gmail.com>',
  ]
  
from django.template import loader
  
from soc.cache import news_feed
from soc.logic.models.news_feed import logic as newsfeed_logic
from soc.views.helper.redirects import getPublicRedirect
from soc.views.helper.redirects import getSubscribeRedirect

# Note: CUSTOM_URL_NAMES is a temporary solution.
# see getFeedUrl for details on the url_name problem.
CUSTOM_URL_NAMES = { 
'studentproject': 'student_project',
'prioritygroup': 'priority_group',
'studentproposal':'student_proposal', 
'groupapp':'group_app', 
'orgapp':'org_app', 
'clubmember':'club_member', 
'organization': 'org'
}


class NewsFeed():
  """
  Render the NewsFeed module or XML of updates for a given entity
  """ 
  
  def __init__(self, entity):
    """ 
    params:
      entity - arbitrary model entity 
    """
    self.entity = entity
  
  def getFeed(self): 
    """gets HTML version of Newsfeed for entity
    """ 
    feed_items = self.retrieveFeed()
    feed_url = self.getFeedUrl()
    context = { 'feed_items': feed_items, 'feed_url': feed_url }
    return loader.render_to_string('soc/news_feed/news_feed.html',
                                     dictionary=context)
    
  def getFeedXML(self):
    """gets XML version of Newsfeed for entity
    """ 
    feed_items = self.retrieveFeed()
    feed_url = self.getFeedUrl()
    template = 'soc/news_feed/news_feed.xml'
    context = {'entity': self.entity, 'feed_items': feed_items, 'feed_url': feed_url }
    return template, context

  @news_feed.cache
  def retrieveFeed(self):
    """ retrieves feed for entity
    """                            
    return newsfeed_logic.retrieveFeed(self.entity)

  def getFeedUrl(self):
    """ retrieve the Feed URL for the entity
    
    TODO(James): 
  
    This temporary method should be superceded by standard methods.
    
    Specifically, url_name should be retrieved from params
    and redirect directly used for subscribe URL.
    
    The issue is that the url_name for one entity (such as a document)
    is required from the view for another entity (such as a site)
    
    The existing url_name val therefore cannot normally be accessed
    from params. 
    
    """ 
    # get the url name
    url_name = CUSTOM_URL_NAMES.get(self.entity.kind().lower())
    if not url_name: 
      url_name = self.entity.kind().lower()
    params = {'url_name': url_name}
    return getSubscribeRedirect(self.entity, params)
    
    
  def linkToEntity(self):
    """ link to entity for a feed item
    """
    url_name = CUSTOM_URL_NAMES.get(self.entity.kind().lower())
    if not url_name: 
      url_name = self.entity.kind().lower()
    params = {'url_name': url_name}
    return getPublicRedirect(self.entity, params)  




