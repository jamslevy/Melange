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
  '"Daniel Diniz" <ajaksu@gmail.com>',
  '"James Levy" <jamesalexanderlevy@gmail.com>',
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
from soc.logic.models.survey import getRoleSpecificFields, GRADES
from soc.logic.models.user import logic as user_logic

from soc.models.survey import Survey
from soc.models.survey_record import SurveyRecord

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
QUESTION_TYPES = {"short_answer": ("Short Answer",
                                   "Less than 40 characters. "
                                   "Rendered as a text input. "
                                   "It's possible to add a free form question"
                                   " (Content) and a in-input propmt/example"
                                   " text."),
                  "choice": ("Selection",
                             "Can be set as a single choice (selection) or "
                             "multiple choice (pick_multi) question. "
                             "Rendered as a select (single choice) or a group "
                             "of checkboxes (multiple choice). "
                            "It's possible to add a free form question"
                            " (Content) and as many free form options as "
                            "wanted. Each option can be edited (double-click), "
                            "deleted (click on (-) button) or reordered (drag "
                            "and drop)."),
                  "long_answer": ("Long Answer",
                                  "Unlimited length, auto-growing field. "
                                  "Rendered as a textarea. "
                                   "It's possible to add a free form question"
                                   " (Content) and a in-input propmt/example"
                                   " text.")
                  }

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
        #'survey_content': forms.fields.CharField(widget=surveys.EditSurvey(),
                                                 #required=False),
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
                                       'take_survey', 'survey_content']
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
    """Survey taking and result display handler.

    For surveys, the "public" page is actually the access-protected
    survey-taking page. We should use a different method name just to
    make this clear.

    Args:
      request: the django request object
      entity: the entity to make public
      context: the context object

    Renders survey taking widget to HTML.

    Checks if user has already submitted form. If so, show existing form
    If we don't want students/mentors to edit the values they've already
    submitted for a survey, this behavior should be altered.

    A deadline can also be used as a conditional for updating values,
    we have a special read_only UI and a check on the POST handler for this.
    Passing read_only=True here allows one to fetch the read_only view.
    """

    # this won't work -- there's *always* a survey entity. We want to
    # check if there is a survey record from this user.
    survey = entity
    user = user_logic.getForCurrentAccount()

    status = self.getStatus(request, context, user, survey)
    read_only, can_write, not_ready = status

    # If user can edit this survey and is requesting someone else's results,
    # in a read-only request, we fetch them.
    if can_write and read_only and 'user_results' in request.GET:
      user = user_logic.getFromKeyNameOr404(request.GET['user_results'])

    if read_only or len(request.POST) == 0 or not_ready:
      # not submitting completed survey record OR we're ignoring late submission
      pass
    else:
      # submitting a completed survey record
      survey_record = SurveyRecord.gql("WHERE user = :1 AND survey = :2",
                                       user, survey).get()
      context['notice'] = "Survey Submission Saved"
      survey_record = survey_logic.updateSurveyRecord(user, survey,
                                                        survey_record,
                                                        request.POST)
    survey_content = survey.survey_content
    survey_record = SurveyRecord.gql("WHERE user = :1 AND survey = :2",
                                     user, survey).get()

    if not survey_record and read_only:
      # No recorded answers, we're either past deadline or want to see answers
      is_same_user = user.key() == user_logic.getForCurrentAccount().key()
      if not can_write or not is_same_user:
        # If user who can edit looks at her own taking page, show the default
        # form as readonly. Otherwise, below, show nothing.
        context["notice"] = "There are no records for this survey and user."
        return False

    survey_form = surveys.SurveyForm(survey_content=survey_content,
                                     this_user=user,
                                     survey_record=survey_record,
                                     read_only=read_only,
                                     editing=False)
    survey_form.getFields()
    if survey.taking_access != "everyone":
      # midterm survey
      # should this be context['survey_form'] ?
      survey_form = getRoleSpecificFields(survey, user, survey_form)

    # Set help and status text
    self.setHelpStatus(context, read_only, survey_record, survey_form, survey)

    if not context['survey_form']:
      access_tpl = "You Must Be a %s to Take This Survey"
      context["notice"] = access_tpl % survey.taking_access.capitalize()

    context['read_only'] = read_only
    return True

  def getStatus(self, request, context, user, survey):
    """Determine if we're past deadline or before opening, check user rights.
    """

    read_only = (context.get("read_only", False) or
                 request.GET.get("read_only", False) or
                 request.POST.get("read_only", False)
                 )
    now = datetime.datetime.now()

    # Check deadline, see check for opening below
    if survey.deadline and now > survey.deadline:
      # Are we already passed the deadline?
      context["notice"] = "The Deadline For This Survey Has Passed"
      read_only = True

    # Check if user can edit this survey
    params = dict(prefix=survey.prefix, scope_path=survey.scope_path)
    checker = access.rights_logic.Checker(survey.prefix)
    roles = checker.getMembership(survey.write_access)
    rights = self._params['rights']
    can_write = access.Checker.hasMembership(rights, roles, params)

    # Check if we're past the opening date
    not_ready = False
    if survey.opening and now < survey.opening:
      not_ready = True
      if not can_write:
        context["notice"] = "There is no such survey available."
        return False
      else:
        context["notice"] = "This survey is not open for taking yet."

    return read_only, can_write, not_ready

  def setHelpStatus(self, context, read_only, survey_record, survey_form,
                    survey):
    """Set help_text and status for template use.
    """

    if not read_only:
      if not survey.deadline: deadline_text = ""
      else: deadline_text = " by " + str(
      survey.deadline.strftime("%A, %d. %B %Y %I:%M%p"))
      if survey_record:
        help_text = "Edit and re-submit this survey" + deadline_text + "."
        status = "edit"
      else:
        help_text = "Please complete this survey" + deadline_text + "."
        status = "create"
    else:
      help_text = "Read-only view."
      status = "view"
    survey_data = dict(survey_form=survey_form, status=status,
                                     help_text=help_text)
    context.update(survey_data)

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
      # New Survey
      fields['author'] = user
    else:
      fields['author'] = entity.author
      schema = self.loadSurveyContent(schema, survey_fields, entity)

    # Remove deleted properties from the model
    self.deleteQuestions(schema, survey_fields, request.POST)

    # Add new text questions and re-build choice questions
    self.getRequestQuestions(schema, survey_fields, request.POST)

    # Get schema options for choice questions
    self.getSchemaOptions(schema, survey_fields, request.POST)

    survey_content = getattr(entity,'survey_content', None)
    # Create or update a SurveyContent for this Survey
    survey_content = survey_logic.createSurvey(survey_fields, schema,
                                                survey_content=survey_content)

    # Enable grading
    if "has_grades" in request.POST and request.POST["has_grades"] == "on":
      survey_content.has_grades = True
    if entity:
      entity.survey_content = survey_content
      db.put(entity)
    else:
      fields['survey_content'] = survey_content

    fields['modified_by'] = user
    super(View, self)._editPost(request, entity, fields)

  def loadSurveyContent(self, schema, survey_fields, entity):
    """Populate the schema dict and get text survey questions.
    """

    if hasattr(entity, 'survey_content'):
      # There is a SurveyContent already
      survey_content = entity.survey_content
      schema = eval(survey_content.schema)
      for question_name in survey_content.dynamic_properties():
        # Get the current questions from the SurveyContent
        if question_name not in schema:
          continue
        if schema[question_name]['type'] not in CHOICE_TYPES:
          # Choice questions are always regenerated from request, see
          # self.get_request_questions()
          question = getattr(survey_content, question_name)
          survey_fields[question_name] = question
    return schema

  def deleteQuestions(self, schema, survey_fields, POST):
    """Process the list of questions to delete, from a hidden input.
    """

    deleted = POST.get('__deleted__', '')
    if deleted:
      deleted = deleted.split(',')
      for d in deleted:
        if d in schema:
          del schema[d]
        if d in survey_fields:
          del survey_fields[d]

  def getRequestQuestions(self, schema, survey_fields, POST):
    """Get fields from request.

    We use two field/question naming and processing schemes:
      - Choice questions consist of <input/>s with a common name, being rebuilt
        anew on every edit POST so we can gather ordering, text changes,
        deletions and additions.
      - Text questions only have special survey__* names on creation, afterwards
        they are loaded from the SurveyContent dynamic properties.
    """

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

  def getSchemaOptions(self, schema, survey_fields, POST):
    """Get question, type, rendering and option order for choice questions.
    """

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

  def createGet(self, request, context, params, seed):
    """Pass the question types for the survey creation template.
    """

    context['question_types'] = QUESTION_TYPES
    # Avoid spurious results from showing on creation
    context['new_survey'] = True
    return super(View, self).createGet(request, context, params, seed)

  def editGet(self, request, entity, context, params=None):
    """Process GET requests for the specified entity.

    Builds the SurveyForm that represents the Survey question contents.
    """

    #XXX:ajaksu shoudn't CHOOSE_A_PROJECT_FIELD and CHOOSE_A_GRADE_FIELD
    # go into a template? Then permission flags on context control display?
    
    # jamtoday: template would work, but isn't necessary.
    # don't understand what you're saying about permissions
    CHOOSE_A_PROJECT_FIELD = """<tr class="role-specific">
    <th><label>Choose Project:</label></th>
    <td>
      <select disabled="TRUE" id="id_survey__NA__selection__project"
        name="survey__1__selection__see">
          <option>Survey Taker's Projects For This Program</option></select>
     </td></tr>
     """
    CHOOSE_A_GRADE_FIELD = """<tr class="role-specific">
    <th><label>Assign Grade:</label></th>
    <td>
      <select disabled=TRUE id="id_survey__NA__selection__grade"
       name="survey__1__selection__see">
        <option>Pass/Fail</option>
      </select></td></tr>
    """

    self._entity = entity
    survey_content = entity.survey_content
    user = user_logic.getForCurrentAccount()
    survey_form = surveys.SurveyForm(survey_content=survey_content,
                                     this_user=user, survey_record=None,
                                     editing=True, read_only=False)
    survey_form.getFields()
    grades = False
    if survey_content:
      grades = survey_content.survey_parent.get().has_grades
    local = dict(survey_form=survey_form, question_types=QUESTION_TYPES,
                grades=grades, survey_h=entity.survey_content)
    context.update(local)

    params['edit_form'] = HelperForm(params['edit_form'])
    # activate grades flag
    if request._get.get('activate'):
      self.grade(request)
    return super(View, self).editGet(request, entity, context, params=params)

  def getMenusForScope(self, entity, params):
    """List featured surveys iff after the opening date and before deadline.
    """

    filter = {
        'prefix' : params['url_name'],
        'scope_path': entity.key().id_or_name(),
        'is_featured': True,
        }

    entities = self._logic.getForFields(filter)
    submenus = []
    # add a link to all featured documents
    now = datetime.datetime.now()
    for entity in entities:
      # Omit if either before opening or after deadline
      if entity.opening and entity.opening > now:
        continue
      if entity.deadline and entity.deadline < now:
        continue
      #TODO only if a document is readable it might be added
      submenu = (redirects.getPublicRedirect(entity, self._params),
                 entity.short_name, 'show')
      submenus.append(submenu)
    return submenus

  def activate(self, request, **kwargs):
    """This is a hack to support the 'Enable grades' button.
    """

    #XXX Should be removed, as the POST/checkbox way works better and
    # we want to separate grading from non-grading surveys
    path = request.path.replace('/activate/', '/edit/')
    return http.HttpResponseRedirect(path + '?activate=1')

  def grade(self, request, **kwargs):
    """Updates SurveyRecord's grades for a given Survey.
    """

    #XXX Needs ACL checks
    #TODO: Move to the survey results page
    prefix = 'id_survey__'
    suffix = '__selection__grade'
    survey_key_name = survey_logic.getKeyNameFromPath(request.path)
    survey = Survey.get_by_key_name(survey_key_name)
    return
    for user, grade in request.POST.items():
      if user.startswith(prefix):
        user = user.replace(prefix, '').replace(suffix, '')
      else:
        continue
      # one alternative would be to store the user key as an id attr 
      # and send it in the request instead of the link_id
      user = User.gql("WHERE link_id = :1", user).get()
      survey_record = SurveyRecord.gql(
          "WHERE user = :1 AND survey = :2", user, survey).get()
      if survey_record:
        survey_record.grade = GRADES[grade]
        survey_record.put()
    #XXX Ditto for this redirect
    return http.HttpResponseRedirect(request.path.replace('/grade/', '/edit/'))


class HelperForm(object):
  """Thin wrapper for adding values to params['edit_form'].fields.
  """

  def __init__(self, form=None):
    """Store the edit_form.
    """

    self.form = form

  def __call__(self, instance=None):
    """Transparently instantiate and add initial values to the edit_form.
    """

    form = self.form(instance=instance)
    form.fields['created_by'].initial = instance.author.name
    form.fields['last_modified_by'].initial = instance.modified_by.name
    form.fields['doc_key_name'].initial = instance.key().id_or_name()
    return form


FIELDS = 'author modified_by'
PLAIN = 'is_featured content created modified'


def _get_csv_header(sur):
  """CSV header helper, needs support for comment lines in CSV.
  """

  tpl = '# %s: %s\n'
  fields = ['# Melange Survey export for \n#  %s\n#\n' % sur.title]
  fields += [tpl % (k,v) for k,v in sur.toDict().items()]
  fields += [tpl % (f, str(getattr(sur, f))) for f in PLAIN.split()]
  fields += [tpl % (f, str(getattr(sur, f).link_id)) for f in FIELDS.split()]
  fields.sort()
  fields += ['#\n#---\n#\n']
  schema =  sur.survey_content.schema
  indent = '},\n#' + ' ' * 9
  fields += [tpl % ('Schema', schema.replace('},', indent)) + '#\n']
  return ''.join(fields).replace('\n', '\r\n')


def _get_records(recs, props):
  """Fetch properties from SurveyRecords for CSV export.
  """

  records = []
  props = props[1:]
  for rec in recs:
    values = tuple(getattr(rec, prop, None) for prop in props)
    leading = (rec.user.link_id,)
    records.append(leading + values)
  return records


def to_csv(survey):
  """CSV exporter.
  """

  try:
    first = survey.survey_records.run().next()
  except StopIteration:
    # Bail out early if survey_records.run() is empty
    return '', survey.link_id
  header = _get_csv_header(survey)
  leading = ['user', 'created', 'modified']
  properties = leading + survey.survey_content.orderedProperties()
  recs = survey.survey_records.run()
  recs = _get_records(recs, properties)
  output = StringIO.StringIO()
  writer = csv.writer(output)
  writer.writerow(properties)
  writer.writerows(recs)
  return header + output.getvalue(), survey.link_id


def notify_students(survey):
  """POC for notification, pending mentor-project linking.
  """

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
