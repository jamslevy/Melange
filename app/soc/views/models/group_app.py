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

"""Views for Group App.
"""

__authors__ = [
    '"Sverre Rabbelier" <sverre@rabbelier.nl>',
    '"Lennard de Rijk" <ljvderijk@gmail.com>',
  ]


from django import forms
from django import http
from django.utils.translation import ugettext

from soc.logic import cleaning
from soc.logic import dicts
from soc.logic.helper import notifications
from soc.logic.models.group_app import logic as group_app_logic
from soc.logic.models.user import logic as user_logic
from soc.views import out_of_band
from soc.views.helper import decorators
from soc.views.helper import lists as list_helper
from soc.views.helper import redirects
from soc.views.helper import responses
from soc.views.helper import widgets
from soc.views.models import base


DEF_APPLICATION_LIST_DESCRIPTION_FMT = ugettext(
    'Overview of %(name_plural)s whose status is "%(status)s"')


class View(base.View):
  """View methods for the Group App model.
  """

  def __init__(self, params=None):
    """Defines the fields and methods required for the base View class
    to provide the user with list, public, create, edit and delete views.

    Params:
      params: a dict with params for this View
    """

    new_params = {}
    new_params['logic'] = group_app_logic

    new_params['name'] = "Group Application"
    new_params['name_short'] = "Group App"

    # use the twoline templates for these questionnaires
    new_params['create_template'] = 'soc/models/twoline_edit.html'
    new_params['edit_template'] = 'soc/models/twoline_edit.html'

    patterns = [(r'^%(url_name)s/(?P<access_type>list_self)/%(scope)s$',
        'soc.views.models.%(module_name)s.list_self',
        'List my %(name_plural)s'),
        (r'^%(url_name)s/(?P<access_type>review_overview)/%(scope)s$',
        'soc.views.models.%(module_name)s.review_overview',
        'List of %(name_plural)s for reviewing'),
        (r'^%(url_name)s/(?P<access_type>review)/%(key_fields)s$',
          'soc.views.models.%(module_name)s.review',
          'Review %(name_short)s')]

    new_params['extra_django_patterns'] = patterns

    new_params['extra_dynaexclude'] = ['applicant', 'backup_admin', 'status',
        'created_on', 'last_modified_on']

    new_params['create_dynafields'] = [
        {'name': 'backup_admin_link_id',
         'base': widgets.ReferenceField,
         'passthrough': ['reference_url', 'required', 'label'],
         'reference_url': 'user',
         'required': False,
         'label': params['logic'].getModel().backup_admin.verbose_name,
         'example_text': ugettext('The link_id of the backup admin'),
         },
         ]

    new_params['create_extra_dynaproperties'] = {
        'email': forms.fields.EmailField(required=True),
        'clean_backup_admin_link_id': 
            cleaning.clean_users_not_same('backup_admin_link_id'),
        }

    new_params['edit_extra_dynaproperties'] = {
        'clean_link_id' : cleaning.clean_link_id('link_id'),
        }

    params = dicts.merge(params, new_params, sub_merge=True)

    super(View, self).__init__(params=params)


  def _editGet(self, request, entity, form):
    """See base.View._editGet().
    """

    if entity.backup_admin:
      form.fields['backup_admin_link_id'].initial = entity.backup_admin.link_id

    super(View, self)._editGet(request, entity, form)

  def _editPost(self, request, entity, fields):
    """See base.View._editPost().
    """

    if not entity:
      # set the applicant field to the current user
      fields['applicant'] = user_logic.getForCurrentAccount()

    #set the backup_admin field with the cleaned link_id
    fields['backup_admin'] = fields['backup_admin_link_id']

    # the application has either been created or edited so
    # the status needs to be set accordingly
    fields['status'] = 'needs review'

    super(View, self)._editPost(request, entity, fields)


  @decorators.merge_params
  @decorators.check_access
  def list(self, request, access_type,
           page_name=None, params=None, filter=None, order=None, **kwargs):
    """Lists all notifications in separate tables, depending on their status.

    for parameters see base.list()
    """

    # create the selection list
    selection = [('needs review', (redirects.getEditRedirect, params)), 
                 ('pre-accepted', (redirects.getEditRedirect, params)),
                 ('accepted', (redirects.getEditRedirect, params)),
                 ('pre-rejected', (redirects.getEditRedirect, params)),
                 ('rejected', (redirects.getEditRedirect, params)),
                 ('ignored', (redirects.getEditRedirect, params)),]

    return self._applicationListConstructor(request, params, page_name, 
        filter=filter, selection=selection, **kwargs)


  def _applicationListConstructor(self, request, params, page_name, filter={}, 
                                  selection=[], **kwargs):
    """Constructs the list containing applications for the given the arguments.
    
    Args:
      filter: This is the filter used for all application
      selection: This is a list containing tuples stating the status for an
        application and the redirect action.
      See base.View.public() for the rest.
    
    Returns:
      HTTP Response containing the list view.

    """

    contents = []
    list_params = params.copy()
    index = 0

    if not filter:
      filter = {}

    for status, action in selection:
      # only select the requests that have been pre-accpeted
      filter['status'] = status

      name = status[0] if isinstance(status, list) else status

      list_params['list_description'] = (
          DEF_APPLICATION_LIST_DESCRIPTION_FMT % (
          {'name_plural': params['name_plural'], 'status': name}))
      list_params['list_action'] = action

      list_content = list_helper.getListContent(
          request, list_params, filter, idx=index)

      contents += [list_content]

      index += 1

    # call the _list method from base to display the list
    if kwargs.get('context'):
      context = kwargs['context']
    else:
      context = {}

    return self._list(request, params, contents, page_name, context=context)


  @decorators.merge_params
  @decorators.check_access
  def listSelf(self, request, access_type,
               page_name=None, params=None, **kwargs):
    """List all applications from the current logged-in user.

    For params see base.View.public().
    """

    user_entity = user_logic.getForCurrentAccount()
    filter = {'applicant' : user_entity}

    if kwargs['scope_path']:
      filter['scope_path'] = kwargs['scope_path']

    # create the selection list
    selection = [(['needs review', 'pre-accepted', 'pre-rejected'],
                  (redirects.getEditRedirect, params)),
                 ('accepted', (redirects.getApplicantRedirect, 
                    {'url_name': params['group_url_name']})),
                 ('rejected', (redirects.getPublicRedirect, params))]

    return self._applicationListConstructor(request, params, page_name,
        filter=filter, selection=selection, **kwargs)

  @decorators.merge_params
  @decorators.check_access
  def review(self, request, access_type,
             page_name=None, params=None, **kwargs):
    """Handles the view containing the review of an application.

    accepted (true or false) in the GET data will mark
    the application accordingly.


    For params see base.View.public().
    """

    try:
      entity = self._logic.getFromKeyFieldsOr404(kwargs)
    except out_of_band.Error, error:
      return responses.errorResponse(
          error, request, template=params['error_public'])

    get_dict = request.GET

    # check to see if we can make a decision for this application
    if 'status' in get_dict.keys():
      status_value = get_dict['status']

      if status_value in ['accepted', 'rejected', 'ignored', 'pre-accepted',
          'pre-rejected']:
        # this application has been properly reviewed update the status

        # only update if the status changes
        if entity.status != status_value:
          fields = {'status' : status_value}

          self._logic.updateEntityProperties(entity, fields)
          self._review(request, params, entity, status_value, **kwargs)

          if status_value == 'accepted':
            # the application has been accepted send out a notification
            notifications.sendNewGroupNotification(entity, params)

        # redirect to the review overview
        fields = {'url_name': params['url_name']}

        scope_path = entity.scope_path

        if not scope_path:
          scope_path = ''

        # add scope_path to the dictionary
        fields['scope_path'] = scope_path

        return http.HttpResponseRedirect(
            '/%(url_name)s/review_overview/%(scope_path)s' %fields)

    # the application has not been reviewed so show the information
    # using the appropriate review template
    params['public_template'] = params['review_template']

    return super(View, self).public(request, access_type,
        page_name=page_name, params=params, **kwargs)


  def _review(self, request, params, app_entity, status, **kwargs):
    """Does any required post review processing.

    Args:
      request: the standard Django HTTP request object
      params: a dict with params for this View
      app_entity: The update application entity
      status: The status that was given to the reviewed app_entity

    """
    pass


  @decorators.merge_params
  @decorators.check_access
  def reviewOverview(self, request, access_type,
             page_name=None, params=None, **kwargs):
    """Displays multiple lists of applications that are in a different
    status of the application process.
    """

    selection = [('needs review', (redirects.getReviewRedirect, params)),
                 ('pre-accepted', (redirects.getReviewRedirect, params)),
                 ('accepted', (redirects.getReviewRedirect, params)),
                 ('pre-rejected', (redirects.getReviewRedirect, params)),
                 ('rejected', (redirects.getReviewRedirect, params)),
                 ('ignored', (redirects.getReviewRedirect, params)),]

    filter = {}

    if kwargs['scope_path']:
      filter['scope_path'] = kwargs['scope_path']

    return self._applicationListConstructor(request, params, page_name,
        filter=filter, selection=selection, **kwargs)

