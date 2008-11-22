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


from google.appengine.ext import db
from google.appengine.api import users

from django import forms
from django.utils.translation import ugettext_lazy

from soc.logic import dicts
from soc.logic import validate
from soc.views import helper
from soc.views.helper import widgets
from soc.views.models import presence

import soc.models.site
import soc.logic.models.site
import soc.logic.dicts
import soc.views.helper
import soc.views.helper.widgets


class CreateForm(presence.SettingsValidationForm):
  """Django form displayed when creating or editing Site Settings.
  """

  class Meta:
    """Inner Meta class that defines some behavior for the form.
    """
    #: db.Model subclass for which the form will gather information
    model = soc.models.site.Site

    #: list of model fields which will *not* be gathered by the form
    exclude = ['inheritance_line', 'home', 'scope', 'scope_path', 'link_id']

  scope_path = forms.CharField(widget=forms.HiddenInput)

  link_id = forms.CharField(widget=forms.HiddenInput)


class EditForm(CreateForm):
  """Django form displayed a Document is edited.
  """

  pass


class View(presence.View):
  """View methods for the Document model.
  """

  def __init__(self, original_params=None):
    """Defines the fields and methods required for the base View class
    to provide the user with list, public, create, edit and delete views.

    Params:
      original_params: a dict with params for this View
    """

    params = {}

    # add ugettext_lazy ?
    params['name'] = "Site Settings"
    params['name_short'] = "Site Settings"
    params['name_plural'] = "Site Settings"
    # lower name and replace " " with "/"
    # for module name lower name and replace " " with "_"
    params['url_name'] = "site/settings"
    params['module_name'] = "site"

    params['edit_form'] = EditForm
    params['create_form'] = CreateForm

    params['lists_template'] = {
      'list_main': 'soc/list/list_main.html',
      'list_pagination': 'soc/list/list_pagination.html',
      'list_row': 'soc/site/list/site_row.html',
      'list_heading': 'soc/site/list/site_heading.html',
    }

    params['delete_redirect'] = '/' + params['url_name'] + '/list'

    params['sidebar_additional'] = [
        ('/' + params['url_name'] + '/edit', 'Edit Main Site Settings')]

    params = dicts.merge(original_params, params)

    presence.View.__init__(self, original_params=params)

    self._logic = soc.logic.models.site.logic

  def main_public(self, request, page_name=None, **kwargs):
    """Displays the main site settings page.

    Args:
      request: the standard Django HTTP request object
      page_name: the page name displayed in templates as page and header title
      kwargs: not used
    """

    keys = self._logic.getKeyFieldNames()

    # No entity in this case, since Site key values are hard-coded for the
    # Site singleton, so pass in None to match parent method footprint.
    values = self._logic.getKeyValues(None)
    key_values = dicts.zip(keys, values)

    return self.public(request, page_name, **key_values)

  def main_edit(self, request, page_name=None, **kwargs):
    """Displays the edit page for the main site settings page.

    Args:
      request: the standard Django HTTP request object
      page_name: the page name displayed in templates as page and header title
      kwargs: not used
    """

    keys = self._logic.getKeyFieldNames()

    # No entity in this case, since Site key values are hard-coded for the
    # Site singleton, so pass in None to match parent method footprint.
    values = self._logic.getKeyValues(None)
    key_values = dicts.zip(keys, values)

    return self.edit(request, page_name, seed=key_values, **key_values)

  def getDjangoURLPatterns(self):
    """See base.View.getDjangoURLPatterns().
    """

    patterns = super(View, self).getDjangoURLPatterns()
    patterns += [(r'^$','soc.views.models.site.main_public')]

    page_name = "Edit Site Settings"
    patterns += [(r'^' + self._params['url_name'] + '/edit$',
                  'soc.views.models.site.main_edit',
                  {'page_name': page_name}, page_name)]
    return patterns

view = View()

create = view.create
edit = view.edit
delete = view.delete
list = view.list
public = view.public
main_public = view.main_public
main_edit = view.main_edit