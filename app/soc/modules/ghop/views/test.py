# Copyright 2009 the Melange authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Module containing a test view.
"""

__authors__ = [
  '"Sverre Rabbelier" <sverre@rabbelier.nl>',
  '"Lennard de Rijk" <ljvderijk@gmail.com>',
  ]


from django import http

from soc.logic import dicts
from soc.modules.ghop.logic.test import logic as test_logic
from soc.views.helper import access
from soc.views.helper import decorators
from soc.views.models import base


class View(base.View):
  """View methods for testing.
  """

  def __init__(self, params=None):
    """Defines the fields and methods required for the base View class
    to provide the user with list, public, create, edit and delete views.

    Params:
      params: a dict with params for this View
    """

    rights = access.Checker(params)
    rights['test'] = ['allow']

    new_params = {}
    new_params['logic'] = test_logic
    new_params['rights'] = rights

    new_params['name'] = 'test'

    # add manage pattern
    patterns = [(r'^%(url_name)s/(?P<access_type>test)$',
        'soc.modules.ghop.views.%(module_name)s.test',
        'Test module.'),]

    new_params['extra_django_patterns'] = patterns

    params = dicts.merge(params, new_params)

    super(View, self).__init__(params=params)

  @decorators.merge_params
  @decorators.check_access
  def test(self, request, access_type,
           page_name=None, params=None, **kwargs):
    """
    """

    return http.HttpResponse('Hello World')


view = View()

test = view.test
