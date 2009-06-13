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
import datetime

import re
import StringIO
from django import forms
from django import http

from google.appengine.ext import db

from soc.cache import home
from soc.logic import cleaning
from soc.logic import dicts
from soc.logic.models.survey import logic as survey_logic
from soc.logic.models.user import logic as user_logic
from soc.models.survey import SurveyRecord, Survey
from soc.models.user import User
from soc.views.helper import access
from soc.views.helper import decorators
from soc.views.helper import redirects
from soc.views.helper import surveys
from soc.views.helper import widgets
from soc.views.models import base


CHOICE_TYPES = set(('selection', 'pick_multi', 'choice'))
TEXT_TYPES = set(('long_answer', 'short_answer'))
PROPERTY_TYPES = tuple(CHOICE_TYPES) + tuple(TEXT_TYPES)


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
         (r'^%(url_name)s/(?P<access_type>grade)/%(scope)s$',
         'soc.views.models.%(module_name)s.grade',
         'Create a new %(name)s'),
        ]

    new_params['export_content_type'] = 'text/text'
    new_params['export_extension'] = '.csv'
    new_params['export_function'] = to_csv
    new_params['delete_redirect'] = '/'
    new_params['list_key_order'] = [
        'link_id', 'scope_path', 'name', 'short_name', 'title',
        'content', 'prefix','read_access','write_access']

    new_params['edit_template'] = 'soc/survey/edit.html'
    new_params['create_template'] = 'soc/survey/edit.html'

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
        # ajaksu: I think we should be adding questions/fields via AJAX,
        # so saving the whole form wouldn't be necessary.
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
    read_only = (context.get("read_only", False) or
                 request.GET.get("read_only", False) or
                 request.POST.get("read_only", False)
                 )
    if this_survey.deadline and datetime.datetime.now() > this_survey.deadline:
      # Are we already passed the deadline?
      context["notice"] = "The Deadline For This Survey Has Passed"
      read_only = True

    # Check if user can edit this survey
    params = dict(prefix=this_survey.prefix, scope_path=this_survey.scope_path)
    checker = access.rights_logic.Checker(this_survey.prefix)
    roles = checker.getMembership(this_survey.write_access)
    can_write = access.Checker.hasMembership(self._params['rights'], roles, params)
    # If user can edit this survey and is requesting someone else's results,
    # in a read-only request, we fetch them.
    if can_write and read_only and 'user_results' in request.GET:
      user = user_logic.getFromKeyNameOr404(request.GET['user_results'])
    survey_record = SurveyRecord.gql("WHERE user = :1 AND this_survey = :2",
                                     user, this_survey ).get()
    if read_only or len(request.POST) == 0:
      # not submitting completed survey record OR we're ignoring late submission
      pass
    else: # submitting a completed survey record
      context['notice'] = "Survey Submission Saved"
      survey_record = survey_logic.update_survey_record(user, this_survey,
                                                        survey_record,
                                                        request.POST)
    take_survey = surveys.TakeSurvey(user=user)
    context['survey_form'] = take_survey.render(this_survey.this_survey,
                                                survey_record,
                                                read_only)
    if not context['survey_form']:
      access_tpl = "You Must Be a %s to Take This Survey"
      context["notice"] = access_tpl % this_survey.taking_access.capitalize()
    context['read_only'] = read_only
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
          if prop in schema and schema[prop]['type'] not in CHOICE_TYPES:
            # Choice questions are always regenerated from request, see
            # self.get_request_questions()
            survey_fields[prop] = getattr(_survey, prop)
    self.delete_questions(schema, survey_fields, request.POST)

    self.get_request_questions(schema, survey_fields, request.POST)

    self.get_schema_options(schema, survey_fields, request.POST)

    this_survey = survey_logic.create_survey(survey_fields, schema,
                      this_survey=getattr(entity,'this_survey', None))

    if "has_grades" in request.POST and request.POST["has_grades"] == "on":
      this_survey.has_grades = True
    if entity:
      entity.this_survey = this_survey
      entity.scope = survey_logic.getProgram(entity)
      db.put(entity)
    else:
      fields['scope'] = this_survey.scope
      # XXX Doesn't work :(
      fields['scope'] = scope
      fields['this_survey'] = this_survey

    fields['modified_by'] = user
    super(View, self)._editPost(request, entity, fields)

  def delete_questions(self, schema, survey_fields, POST):
    deleted = POST.get('__deleted__', '')
    if deleted:
      deleted = deleted.split(',')
      for d in deleted:
        if d in schema:
          del schema[d]
        if d in survey_fields:
          del survey_fields[d]

  def get_request_questions(self, schema, survey_fields, POST):
    # Get fields from request
    for key, value in POST.items():
      if key.startswith('id_'):
        # Choice question fields, they are always generated from POST contents,
        # as their 'content' is editable and they're reorderable.
        # Also get its field index for handling reordering.
        name, number = key[3:].replace('__field', '').rsplit('_', 1)
        if name not in schema:
          if 'NEW_' + name in POST:
            # New Choice question, set generic type and get its index
            schema[name] = {'type': 'choice'}
            schema[name]['index'] = int(POST['index_for_' + name])
        if name in schema and schema[name]['type'] in CHOICE_TYPES:
          # Build an index:content dictionary
          if name in survey_fields:
            if value not in survey_fields[name]:
              survey_fields[name][int(number)] = value
          else:
            survey_fields[name] = {int(number): value}

      elif key.startswith('survey__'):
        # New Text question
        # This is super ugly but unless data is serialized the regex
        # is needed
        prefix = re.compile('survey__([0-9]{1,3})__')
        prefix_match = re.match(prefix, key)
        index = prefix_match.group(0).replace('survey', '').replace('__','')
        index = int(index)
        field_name = prefix.sub('', key)
        field = 'id_' + key
        for ptype in PROPERTY_TYPES:
          # should only match one
          if ptype + "__" in field_name:
            field_name = field_name.replace(ptype + "__", "")
            schema[field_name] = {}
            schema[field_name]["index"] = index
            schema[field_name]["type"] = ptype
        survey_fields[field_name] = value

  def get_schema_options(self, schema, survey_fields, POST):
    RENDER = {'checkboxes': 'multi_checkbox', 'select': 'single_select'}
    for key in schema:
      if schema[key]['type'] in CHOICE_TYPES and key in survey_fields:
        # Handle reordering fields
        ordered = False
        type_for = 'type_for_' + key
        if type_for in POST:
          schema[key]['type'] = POST[type_for]
        render_for = 'render_for_' + key
        if render_for in POST:
          schema[key]['render'] = RENDER[POST[render_for]]
        order = 'order_for_' + key
        if order in POST and isinstance(survey_fields[key], dict):
          # 'order_for_name' is jquery serialized from a sortable, so it's in
          # a 'name[]=1&name[]=2&name[]=0' format ('id-li-' is set in our JS)
          order = POST[order]
          order = order.replace('id-li-%s[]=' % key, '')
          order = order.split('&')
          if len(order) == len(survey_fields[key]) and order[0]:
            order = [int(number) for number in order]
            if set(order) == set(survey_fields[key]):
              survey_fields[key] = [survey_fields[key][i] for i in order]
              ordered = True
          if not ordered:
            # We don't have a good ordering to use
            ordered = sorted(survey_fields[key].items())
            survey_fields[key] = [value for index, value in ordered]

      # Set 'question' entry (free text label for question) in schema
      question_for = 'NEW_' + key
      if question_for in POST:
        schema[key]["question"] = POST[question_for]

  def _editGet(self, request, entity, form):
    """See base.View._editGet().
    This is only for editing existing surveys
    """

    self._entity = entity
    if 'notify' in request.GET:
      if request.GET['notify'] == 'students':
        notify_students(entity)

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

  def grade(self, request, **kwargs):
    #XXX Needs ACL checks
    prefix = 'id_survey__'
    suffix = '__selection__grade'
    link_id = request.path.split('/')[-1].split('?')[0]
    #XXX There has to be better way to do this than this gql :-)
    this_survey = Survey.gql("WHERE link_id = :1", link_id).get()
    for user, grade in request.POST.items():
      if user.startswith(prefix):
        user = user.replace(prefix, '').replace(suffix, '')
      else:
        continue
      user = User.gql("WHERE link_id = :1", user).get()
      survey_record = SurveyRecord.gql(
          "WHERE user = :1 AND this_survey = :2", user, this_survey ).get()
      if survey_record:
        survey_record.grade = grade
        survey_record.put()
    #XXX Ditto for this redirect
    return http.HttpResponseRedirect(request.path.replace('/grade/', '/edit/'))


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

def notify_students(survey):
  from soc.models.student import Student
  from soc.models.program import Program
  from soc.logic.helper import notifications
  notify = notifications.sendNotification
  scope = Program.get_by_key_name(survey.scope_path)
  students = Student.gql("WHERE scope = :1", scope).run()
  have_answered = set([rec.user.key() for rec in survey.survey_records.run()])
  creator = survey.author
  path = (survey.entity_type().lower(), survey.prefix,
          survey.scope_path, survey.link_id)
  url = "/%s/show/%s/%s/%s" % path
  props = dict(survey_url=url, survey_title=survey.title)
  tpl = 'soc/survey/messages/new_survey.html'
  subject = 'New Survey: "%s"' % survey.title
  for student in students:
    if student.user.key() not in have_answered:
      notify(student.user, creator, props, subject, tpl)




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
grade = decorators.view(view.grade)
