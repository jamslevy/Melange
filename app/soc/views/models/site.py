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

"""Views for Site Settings.
"""

__authors__ = [
    '"Sverre Rabbelier" <sverre@rabbelier.nl>',
  ]


from django import forms
from django.utils.translation import ugettext

from soc.logic import cleaning
from soc.logic import dicts
from soc.views import out_of_band
from soc.views.helper import access
from soc.views.helper import decorators
from soc.views.helper.news_feed import NewsFeed
from soc.views.helper import redirects
from soc.views.helper import responses
from soc.views.helper import widgets
from soc.views.models import document as document_view
from soc.views.models import presence_with_tos

import soc.models.site
import soc.logic.models.site
import soc.logic.dicts
import soc.logic.system


class View(presence_with_tos.View):
  """View methods for the Document model.
  """

  def __init__(self, params=None):
    """Defines the fields and methods required for the base View class
    to provide the user with list, public, create, edit and delete views.

    Params:
      params: a dict with params for this View
    """

    rights = access.Checker(params)
    rights['unspecified'] = ['checkIsDeveloper']
    rights['any_access'] = ['allow']
    rights['show'] = ['checkIsDeveloper']

    new_params = {}
    new_params['logic'] = soc.logic.models.site.logic
    new_params['rights'] = rights

    new_params['name'] = "Site Settings"
    new_params['name_plural'] = new_params['name']
    new_params['document_prefix'] = 'site'
    new_params['name_short'] = "Site"

    new_params['sidebar_defaults'] = [('/%s/edit', 'Edit %(name)s', 'edit')]
    new_params['sidebar_heading'] = new_params['name_short']

    new_params['edit_template'] = 'soc/site/edit.html'
    new_params['home_template'] = 'soc/site/home.html'

    new_params['create_extra_dynaproperties'] = {
        'link_id': forms.CharField(widget=forms.HiddenInput, required=True),
        'noreply_email': forms.EmailField(required=False),
        }
    new_params['edit_extra_dynaproperties'] = {
        'link_id': forms.CharField(widget=forms.HiddenInput, required=True),
        'home_link_id': widgets.ReferenceField(
            reference_url='document', required=False,
            filter_fields={'prefix': new_params['document_prefix']},
            label=ugettext('Home page Document link ID'),
            help_text=soc.models.work.Work.link_id.help_text),
        'tos_link_id': widgets.ReferenceField(
            reference_url='document', required=False,
            filter_fields={'prefix': new_params['document_prefix']},
            label=ugettext('Terms of Service Document link ID'),
            help_text=soc.models.work.Work.link_id.help_text),
        }

    patterns = []

    page_name = "Home Page"
    patterns += [(r'^$', 'soc.views.models.%(module_name)s.main_public',
                  page_name)]

    page_name = "Edit Site"
    patterns += [(r'^%(url_name)s/(?P<access_type>edit)$',
                  'soc.views.models.%(module_name)s.main_edit',
                  page_name)]

    if soc.logic.system.isDebug():
      patterns += [('^seed_db$', 'soc.models.seed_db.seed', "Seed DB"),
                   ('^clear_db$', 'soc.models.seed_db.clear', "Clear DB"),
                   ('^reseed_db$', 'soc.models.seed_db.reseed', "Reseed DB"),
                   ('^seed_many$', 'soc.models.seed_db.seed_many', "Seed Many"),
                   ('^new_seed_many$', 'soc.models.seed_db.new_seed_many',
                    "New Seed Many"),
                   ]

    new_params['extra_django_patterns'] = patterns

    params = dicts.merge(params, new_params)

    super(View, self).__init__(params=params)

  def getSidebarMenus(self, id, user, params=None):
    """See base.View.getSidebarMenus.

    Returns a custom sidebar entry for the 'site' singleton.
    """

    entity = self._logic.getSingleton()

    submenus = document_view.view.getMenusForScope(entity, self._params)

    try:
      rights = self._params['rights']
      rights.setCurrentUser(id, user)
      rights.checkIsHost()
      is_host = True
    except out_of_band.Error:
      is_host = False

    if is_host:
      submenus += [(redirects.getCreateDocumentRedirect(entity, 'site'),
          "Create a New Document", 'any_access')]

      submenus += [(redirects.getListDocumentsRedirect(entity, 'site'),
          "List Documents", 'any_access')]
    submenus += [('/priority_group/list', "List Priority Groups", 'edit')]
    submenus += [('/job/list', "List Jobs", 'edit')]

    new_params = {}
    new_params['sidebar_additional'] = submenus

    params = dicts.merge(params, new_params)
    return super(View, self).getSidebarMenus(id, user, params=params)

  def mainPublic(self, request, page_name=None, **kwargs):
    """Displays the main site settings page.

    Args:
      request: the standard Django HTTP request object
      page_name: the page name displayed in templates as page and header title
      kwargs: not used
    """

    keys = self._logic.getKeyFieldNames()

    # No entity in this case, since Site key values are hard-coded for the
    # Site singleton, so pass in None to match parent method footprint.
    values = self._logic.getKeyValuesFromEntity(None)
    key_values = dicts.zip(keys, values)

    return self.home(request, "home", page_name=page_name, **key_values)

  def mainEdit(self, request, page_name=None, **kwargs):
    """Displays the edit page for the main site settings page.

    Args:
      request: the standard Django HTTP request object
      page_name: the page name displayed in templates as page and header title
      kwargs: not used
    """

    keys = self._logic.getKeyFieldNames()

    # No entity in this case, since Site key values are hard-coded for the
    # Site singleton, so pass in None to match parent method footprint.
    values = self._logic.getKeyValuesFromEntity(None)
    key_values = dicts.zip(keys, values)

    return self.edit(request, "edit", page_name, seed=key_values, **key_values)


  def _public(self, request, entity, context):
    """See base.View._public().
    """

    news_feed = NewsFeed(entity)
    context['news_feed'] = news_feed.getFeed() 
    
view = View()

admin = decorators.view(view.admin)
create = decorators.view(view.create)
edit = decorators.view(view.edit)
delete = decorators.view(view.delete)
list = decorators.view(view.list)
public = decorators.view(view.public)
export = decorators.view(view.export)
main_public = decorators.view(view.mainPublic)
main_edit = decorators.view(view.mainEdit)
home = decorators.view(view.home)
subscribe = decorators.view(view.subscribe)
