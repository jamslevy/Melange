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

"""Views for Surveys.
"""

__authors__ = [
  'JamesLevy" <jamesalexanderlevy@gmail.com>',
  ]

import csv
import re
import StringIO
from django import forms
from django import http

from soc.cache import home
from soc.logic import cleaning
from soc.logic import dicts
from soc.logic.models.survey import logic as survey_logic
from soc.logic.models.user import logic as user_logic
import soc.models.survey
from soc.views.helper import access
from soc.views.helper import decorators
from soc.views.helper import redirects
from soc.views.helper import widgets, surveys
from soc.views.models import base


class View(base.View):
  """View methods for the Survey model.
  """

  def __init__(self, params=None):
    """Defines the fields and methods required for the base View class
    to provide the user with list, public, create, edit and delete views.

    Params:
      params: a dict with params for this View

    TODO: Read/Write Access Needs to Match Survey
    Usage Requirements
    """

    rights = access.Checker(params)
    rights['any_access'] = ['allow']
    rights['show'] = ['checkIsSurveyReadable']
    rights['create'] = ['checkIsUser']
    rights['edit'] = ['checkIsSurveyWritable']
    rights['delete'] = ['checkIsSurveyWritable']
    rights['list'] = ['checkDocumentList']
    rights['pick'] = ['checkDocumentPick']
    rights['grade'] = ['checkIsSurveyGradable']

    new_params = {}
    new_params['logic'] = survey_logic
    new_params['rights'] = rights

    new_params['name'] = "Survey"
    new_params['pickable'] = True

    new_params['extra_django_patterns'] = [
        (r'^%(url_name)s/(?P<access_type>activate)/%(scope)s$',
         'soc.views.models.%(module_name)s.activate',
         'Create a new %(name)s'),
        ]

    new_params['export_content_type'] = 'text/text'
    new_params['export_extension'] = '.csv'
    new_params['export_function'] = to_csv
    new_params['delete_redirect'] = '/'
    new_params['list_key_order'] = [
        'link_id', 'scope_path', 'name', 'short_name', 'title',
        'content', 'prefix','read_access','write_access']

    
    new_params['create_template'] = 'soc/survey/edit.html'
    new_params['edit_template'] = 'soc/survey/edit.html'

    # which one of these are leftovers from Document?
    new_params['no_create_raw'] = True
    new_params['no_create_with_scope'] = True
    new_params['no_create_with_key_fields'] = True
    new_params['no_list_raw'] = True
    new_params['sans_link_id_create'] = True
    new_params['sans_link_id_list'] = True

    new_params['create_dynafields'] = [
        {'name': 'link_id',
         'base': forms.fields.CharField,
         'label': 'Survey Link ID',
         },
        ]

    new_params['create_extra_dynaproperties'] = {
        'survey_content': forms.fields.CharField(widget=surveys.EditSurvey(),
                                                 required=False),
        # TODO: save survey content when the POST fails
        # Is there a better way to do this besides a hidden field?
        'survey_html': forms.fields.CharField(widget=forms.HiddenInput,
                                              required=False),
        'scope_path': forms.fields.CharField(widget=forms.HiddenInput,
                                             required=True),
        'prefix': forms.fields.CharField(widget=widgets.ReadOnlyInput(),
                                        required=True),
        'clean_content': cleaning.clean_html_content('content'),
        'clean_link_id': cleaning.clean_link_id('link_id'),
        'clean_scope_path': cleaning.clean_scope_path('scope_path'),
        'clean': cleaning.validate_document_acl(self, True),
        }
    new_params['extra_dynaexclude'] = ['author', 'created', 'content',
                                       'home_for', 'modified_by', 'modified',
                                       'take_survey', 'this_survey']
    new_params['edit_extra_dynaproperties'] = {
        'doc_key_name': forms.fields.CharField(widget=forms.HiddenInput),
        'created_by': forms.fields.CharField(widget=widgets.ReadOnlyInput(),
                                             required=False),
        'last_modified_by': forms.fields.CharField(
                                widget=widgets.ReadOnlyInput(), required=False),
        'clean': cleaning.validate_document_acl(self),
        }
    params = dicts.merge(params, new_params)
    super(View, self).__init__(params=params)

  def list(self, request, access_type, page_name=None, params=None,
           filter=None, order=None, **kwargs):
    """See base.View.list.
    """

    return super(View, self).list(request, access_type, page_name=page_name,
                                  params=params, filter=kwargs)

  def _public(self, request, entity, context):
    """
    
    For surveys, the "public" page is actually the access-protected 
    survey-taking page. We should use a different method name just to 
    make this clear. 

    Args:
      request: the django request object
      entity: the entity to make public
      context: the context object
    """

    # this won't work -- there's *always* a survey entity. We want to 
    # check if there is a survey record from this user. 
    this_survey = entity
    user = user_logic.getForCurrentAccount()
    
    import datetime
    if this_survey.deadline and datetime.datetime.now() > this_survey.deadline:
      # Are we already passed the deadline?
      context["notice"] = "The Deadline For This Survey Has Passed"
      return True
    survey_record = soc.models.survey.SurveyRecord.gql("WHERE user = :1 AND this_survey = :2",
                                     user, this_survey ).get() 
    if len(request.POST) == 0: # not submitting completed survey record
      pass
    else: # submitting a completed survey record
      context['notice'] = "Survey Submission Saved"
      survey_record = survey_logic.update_survey_record(user, this_survey, survey_record, request.POST)
    from soc.views.helper.surveys import TakeSurvey
    take_survey = TakeSurvey(user = user)
    context['survey_form'] = take_survey.render(this_survey.this_survey, survey_record)
    if not context['survey_form']:
      context["notice"] = "You Must Be a %s to Take This Survey" % this_survey.taking_access.capitalize()
      
    return True

  def _editContext(self, request, context):
    """Performs any required processing on the context for edit pages.

    Args:
      request: the django request object
      context: the context dictionary that will be used

      Adds list of SurveyRecord results as supplement to view.

      See surveys.SurveyResults for details.
    """

    if not getattr(self, '_entity', None): return
    results = surveys.SurveyResults()

    context['survey_records'] = results.render(self._entity, self._params,
                                             filter={})
                                             
    super(View, self)._editContext(request, context)

  def _editPost(self, request, entity, fields):
    """See base.View._editPost().

    Processes POST request items to add new dynamic field names,
    question types, and default prompt values to SurveyContent model.
    """

    user = user_logic.getForCurrentAccount()
    schema = {}
    survey_fields = {}
    if not entity:
      fields['author'] = user
    else:
      fields['author'] = entity.author
      if hasattr(entity, 'this_survey'):
        _survey = entity.this_survey
        schema = _survey.get_schema()
        for prop in _survey.dynamic_properties():
          survey_fields[prop] = getattr(_survey, prop)
    deleted = request.POST.get('__deleted__', '')
    if deleted:
      deleted = deleted.split(',')
      for d in deleted:
        if d in schema:
          del schema[d]
        if d in survey_fields:
          del survey_fields[d]
    PROPERTY_TYPES = ('long_answer', 'short_answer', 'selection', 'pick_multi')
    for key, value in request.POST.items():
      if key.startswith('survey__'):
        # This is super ugly but unless data is serialized the regex
        # is needed
        prefix = re.compile('survey__([0-9]{1,3})__')
        prefix_match = re.match(prefix, key)
        index = prefix_match.group(0).replace('survey', '').replace('__','')
        index = int(index)
        field_name = prefix.sub('', key)
        for type in PROPERTY_TYPES:
          # should only match one
          if type + "__" in field_name:
            field_name = field_name.replace(type + "__", "")
            schema[field_name] = {}
            schema[field_name]["index"] = index
            schema[field_name]["type"] = type
            if type == "selection":
              value = str(value.split(','))
            elif type == "pick_multi":
              # We may get many values for each key
              value = request.POST.getlist(key)
              value = [val.replace('id_' + key + '__','') for val in value]
        survey_fields[field_name] = value
    this_survey = survey_logic.create_survey(survey_fields, schema,
                      this_survey=getattr(entity,'this_survey', None))
    if entity:
      entity.this_survey = this_survey
    else:
      fields['this_survey'] = this_survey

    fields['modified_by'] = user
    super(View, self)._editPost(request, entity, fields)

  def _editGet(self, request, entity, form):
    """See base.View._editGet().
    This is only for editing existing surveys
    """

    self._entity = entity

    if 'activate' in request.GET and int(request.GET['activate']):
      self._entity.has_grades = True
      self._entity.put()
    form.fields['survey_content'] = forms.fields.CharField(
        widget=surveys.EditSurvey(survey_content=entity.this_survey),
        required=False)
    form.fields['created_by'].initial = entity.author.name
    form.fields['last_modified_by'].initial = entity.modified_by.name
    form.fields['doc_key_name'].initial = entity.key().id_or_name()
    super(View, self)._editGet(request, entity, form)

  def getMenusForScope(self, entity, params):
    """
    From Document view - needed for surveys?
    """

    filter = {
        'prefix' : params['url_name'],
        'scope_path': entity.key().id_or_name(),
        'is_featured': True,
        }

    entities = self._logic.getForFields(filter)
    submenus = []
    # add a link to all featured documents
    for entity in entities:
      #TODO only if a document is readable it might be added
      submenu = (redirects.getPublicRedirect(entity, self._params),
                 entity.short_name, 'show')
      submenus.append(submenu)
    return submenus

  def activate(self, request, **kwargs):
    path = request.path.replace('/activate/', '/edit/')
    return http.HttpResponseRedirect(path + '?activate=1')


FIELDS = 'author modified_by'
PLAIN = 'is_featured content created modified'


def get_csv_header(sur):
  tpl = '# %s: %s\n'
  fields = ['# Melange Survey export for \n#  %s\n#\n' % sur.title]
  fields += [tpl % (k,v) for k,v in sur.toDict().items()]
  fields += [tpl % (f, str(getattr(sur, f))) for f in PLAIN.split()]
  fields += [tpl % (f, str(getattr(sur, f).link_id)) for f in FIELDS.split()]
  fields.sort()
  fields += ['#\n#---\n#\n']
  schema =  str(sur.this_survey.get_schema())
  indent = '},\n#' + ' ' * 9
  fields += [tpl % ('Schema', schema.replace('},', indent)) + '#\n']
  return ''.join(fields).replace('\n', '\r\n')


def get_records(recs, props):
  records = []
  props = props[1:]
  for rec in recs:
    values = tuple(getattr(rec, prop, None) for prop in props)
    records.append((rec.user.link_id,) + values)
  return records


def to_csv(survey):
  """CSV exporter"""

  try:
    first = survey.survey_records.run().next()
  except StopIteration:
    # Bail out early if survey_records.run() is empty
    return '', survey.link_id
  header = get_csv_header(survey)
  properties = ['user'] + survey.this_survey.ordered_properties()
  recs = survey.survey_records.run()
  recs = get_records(recs, properties)
  output = StringIO.StringIO()
  writer = csv.writer(output)
  writer.writerow(properties)
  writer.writerows(recs)
  return header + output.getvalue(), survey.link_id


view = View()

admin = decorators.view(view.admin)
create = decorators.view(view.create)
edit = decorators.view(view.edit)
delete = decorators.view(view.delete)
list = decorators.view(view.list)
public = decorators.view(view.public)
export = decorators.view(view.export)
pick = decorators.view(view.pick)
activate = decorators.view(view.activate)
