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
  
from soc.cache import news_feed

class NewsFeed():
  
  def __init__(self, entity):
    self.entity = entity
  
  
  def getFeed(self): 
    from django.template import loader
    feed_items = self.retrieveFeed()
    feed_url = self.getFeedUrl()
    context = { 'feed_items': feed_items, 'feed_url': feed_url }
    return loader.render_to_string('soc/news_feed/news_feed.html',
                                     dictionary=context)
    

  def getFeedXML(self): 
    feed_items = self.retrieveFeed()
    feed_url = self.getFeedUrl()
    template = 'soc/news_feed/news_feed.xml'
    context = {'entity': self.entity, 'feed_items': feed_items, 'feed_url': feed_url }
    return template, context


  @news_feed.cache
  def retrieveFeed(self):                            
    from soc.logic.models.news_feed import logic as newsfeed_logic
    return newsfeed_logic.retrieveFeed(self.entity)

  def getFeedUrl(self): 
    # should this be in redirects module? 
    #return self.entity.sc
    
    # get the url name
    from soc.logic.models.news_feed import CUSTOM_URL_NAMES
    url_name = CUSTOM_URL_NAMES.get(self.entity.kind().lower())
    if not url_name: url_name = self.entity.kind().lower()
    # return formatted link
    return "/%s/subscribe/%s" % (url_name, self.entity.key().name() )
    
