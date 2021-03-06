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

"""Views for Requests.
"""

__authors__ = [
    '"Sverre Rabbelier" <sverre@rabbelier.nl>',
    '"Lennard de Rijk" <ljvderijk@gmail.com>',
    '"Pawel Solyga" <pawel.solyga@gmail.com>',
  ]


from django import forms
from django import http
from django.utils.translation import ugettext

from soc.logic import cleaning
from soc.logic import dicts
from soc.logic.models import user as user_logic
from soc.views import helper
from soc.views.helper import access
from soc.views.helper import decorators
from soc.views.helper import dynaform
from soc.views.helper import redirects
from soc.views.helper import responses
from soc.views.helper import widgets
from soc.views.models import base

import soc.models.request
import soc.logic.models.request
import soc.logic.dicts
import soc.views.helper
import soc.views.helper.lists
import soc.views.helper.responses


class View(base.View):
  """View methods for the Request model.
  """

  def __init__(self, params=None):
    """Defines the fields and methods required for the base View class
    to provide the user with list, public, create, edit and delete views.

    Params:
      params: a dict with params for this View
    """

    rights = access.Checker(params)
    rights['listSelf'] = ['checkIsUser']
    rights['create'] = ['deny']
    rights['edit'] = ['checkIsDeveloper']
    rights['process_invite'] = ['checkIsMyGroupAcceptedRequest']
    rights['list'] = ['checkIsDeveloper']
    rights['delete'] = ['checkIsDeveloper']
    rights['roles'] = ['checkIsUser']

    new_params = {}
    new_params['rights'] = rights
    new_params['logic'] = soc.logic.models.request.logic

    new_params['name'] = "Request"

    new_params['sidebar_defaults'] = [('/%s/list', 'List %(name_plural)s', 
        'list')]

    new_params['create_template'] = ['soc/request/create.html']

    new_params['extra_dynaexclude'] = ['status', 'role_verbose', 'created_on']

    new_params['create_extra_dynaproperties'] = {
        'link_id': widgets.ReferenceField(reference_url='user'),
        'role': forms.CharField(widget=widgets.ReadOnlyInput(),
                                   required=True),
        'clean_link_id': cleaning.clean_existing_user('link_id'),
        }

    new_params['edit_extra_dynaproperties'] = {
        'scope_path': forms.CharField(widget=forms.HiddenInput,
                                        required=True),
        }

    patterns = [(r'^%(url_name)s/(?P<access_type>process_invite)/'
          '%(key_fields)s$',
          'soc.views.models.%(module_name)s.process_invite',
          'Process Invite to become')]

    new_params['extra_django_patterns'] = patterns

    new_params['invite_processing_template'] = 'soc/request/process_invite.html'
    new_params['request_processing_template'] = \
        'soc/request/process_request.html'

    params = dicts.merge(params, new_params)

    super(View, self).__init__(params=params)

    # create and store the special forms for invite and requests
    self._params['invite_form'] = self._params['create_form']

    updated_fields = {
        'link_id': forms.CharField(widget=widgets.ReadOnlyInput(),
            required=True),
        'group_id': forms.CharField(widget=widgets.ReadOnlyInput(),
            required=True)}

    request_form = dynaform.extendDynaForm(
        dynaform = self._params['create_form'],
        dynaproperties = updated_fields)

    self._params['request_form'] = request_form


  @decorators.merge_params
  @decorators.check_access
  def processInvite(self, request, access_type,
                   page_name=None, params=None, **kwargs):
    """Creates the page upon which an invite can be processed.

    Args:
      request: the standard Django HTTP request object
      access_type : the name of the access type which should be checked
      page_name: the page name displayed in templates as page and header title
      params: a dict with params for this View
      kwargs: the Key Fields for the specified entity
    """

    # get the context for this webpage
    context = responses.getUniversalContext(request)
    helper.responses.useJavaScript(context, params['js_uses_all'])

    request_logic = params['logic']

    # get the request entity using the information from kwargs
    fields = {'link_id': kwargs['link_id'],
        'scope_path': kwargs['scope_path'],
        'role': kwargs['role'],
        'status': 'group_accepted'}
    request_entity = request_logic.getForFields(fields, unique=True)

    # set the page name using the request_entity
    context['page_name'] = '%s %s' % (page_name, 
        request_entity.role_verbose)

    get_dict = request.GET

    if 'status' in get_dict.keys():
      if get_dict['status'] == 'rejected':
        # this invite has been rejected mark as rejected
        request_logic.updateEntityProperties(request_entity, {
            'status': 'rejected'})

        # redirect to user request overview
        return http.HttpResponseRedirect('/user/requests')

    # put the entity in the context
    context['entity'] = request_entity
    context['module_name'] = params['module_name']
    context['invite_accepted_redirect'] = (
        redirects.getInviteAcceptedRedirect(request_entity, self._params))

    #display the invite processing page using the appropriate template
    template = params['invite_processing_template']

    return responses.respond(request, template, context=context)

  @decorators.merge_params
  @decorators.check_access
  def listSelf(self, request, access_type,
               page_name=None, params=None, **kwargs):
    """Displays the unhandled requests for this user.

    Args:
      request: the standard Django HTTP request object
      access_type : the name of the access type which should be checked
      page_name: the page name displayed in templates as page and header title
      params: a dict with params for this View
      kwargs: not used
    """

    # get the current user
    user_entity = user_logic.logic.getForCurrentAccount()

    # construct the Unhandled Invites list

    # only select the Invites for this user that haven't been handled yet
    # pylint: disable-msg=E1103
    filter = {'link_id': user_entity.link_id,
              'status': 'group_accepted'}

    uh_params = params.copy()
    uh_params['list_action'] = (redirects.getInviteProcessRedirect, None)
    uh_params['list_description'] = ugettext(
        "An overview of your unhandled invites.")

    uh_list = helper.lists.getListContent(
        request, uh_params, filter, idx=0)

    # construct the Open Requests list

    # only select the requests from the user
    # that haven't been accepted by an admin yet
    filter = {'link_id': user_entity.link_id,
              'status': 'new'}

    ar_params = params.copy()
    ar_params['list_description'] = ugettext(
        "List of your pending requests.")

    ar_list = helper.lists.getListContent(
        request, ar_params, filter, idx=1)

    # fill contents with all the needed lists
    contents = [uh_list, ar_list]

    # call the _list method from base to display the list
    return self._list(request, params, contents, page_name)


view = View()

admin = decorators.view(view.admin)
create = decorators.view(view.create)
edit = decorators.view(view.edit)
delete = decorators.view(view.delete)
list = decorators.view(view.list)
list_self = decorators.view(view.listSelf)
process_invite = decorators.view(view.processInvite)
public = decorators.view(view.public)
export = decorators.view(view.export)

