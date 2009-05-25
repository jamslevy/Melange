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

"""Custom widgets used for form fields.
"""

__authors__ = [
  'JamesLevy" <jamesalexanderlevy@gmail.com>',
  ]

from django import forms
from django.forms import widgets
from django.template import loader

from google.appengine.ext.db import djangoforms

from soc.logic import dicts
from soc.logic.lists import Lists
from soc.logic.models.user import logic as user_logic
from soc.logic.models.survey import results_logic
from soc.models.survey import SurveyContent, SurveyRecord

class SurveyForm(djangoforms.ModelForm):
  def __init__(self, *args, **kwargs):
    """ This class is used to produce survey forms for several
    circumstances:

    - Admin creating survey from scratch
    - Admin updating existing survey
    - User taking survey
    - User updating already taken survey

    Using dynamic properties of the this_survey model (if passed
    as an arg) the survey form is dynamically formed.

    TODO: Form now scrambles the order of fields. If it's important
    that fields are listed in a certain order, an alternative to
    the schema dictionary will have to be used.
    """

    self.kwargs = kwargs
    self.this_survey = self.kwargs.get('this_survey', None)
    self.survey_record = self.kwargs.get('survey_record', None)
    del self.kwargs['this_survey']
    del self.kwargs['survey_record']
    super(SurveyForm, self).__init__(*args, **self.kwargs)

  def get_fields(self):
    if not self.this_survey: return
    kwargs = self.kwargs
    self.survey_fields = {}
    schema = self.this_survey.get_schema()
    for property in self.this_survey.dynamic_properties():
      if self.survey_record: # use previously entered value
        value = getattr(self.survey_record, property)
      else: # use prompts set by survey creator
        value = getattr(self.this_survey, property)
      if property not in schema: continue
      # correct answers? Necessary for grading
      if schema[property]["type"] == "long_answer":
        self.survey_fields[property] = forms.fields.CharField(
                                    widget=widgets.Textarea(),initial=value)
                                    #custom rows
      if schema[property]["type"] == "short_answer":
        self.survey_fields[property] = forms.fields.CharField(
                                    max_length=40,initial=value)
      if schema[property]["type"] == "selection":
        these_choices = []
        # add all properties, but select chosen one
        options = eval(getattr(self.this_survey, property))
        if self.survey_record:
          these_choices.append((value, value))
          options.remove(value)
        for option in options:
          these_choices.append((option, option))
        self.survey_fields[property] = forms.ChoiceField(choices=tuple(these_choices),
                                              widget=forms.Select())
    return self.insert_fields()

  def insert_fields(self):
    survey_order = self.this_survey.get_survey_order()
    for position, property in survey_order.items():
      self.fields.insert(position, property, self.survey_fields[property])
    return self.fields

  class Meta(object):
    model = SurveyContent
    exclude = ['schema']





class EditSurvey(widgets.Widget):
  """Edit Survey, or Create Survey if not this_survey arg given.
  """

  WIDGET_HTML = """
  <div id="survey_widget"><table> %(survey)s </table> %(options_html)s </div>
  <script type="text/javascript" src="/soc/content/js/jquery.growfield.packed-1.1.js"></script>
  <script type="text/javascript" src="/soc/content/js/edit_survey.js"></script>
  """
  QUESTION_TYPES = {"short_answer": "Short Answer", "selection": "Selection",
                    "long_answer": "Long Answer", }
  BUTTON_TEMPLATE = """
  <button id="%(type_id)s" onClick="return false;">Add %(type_name)s Question</button>
  """
  OPTIONS_HTML = """
  <div id="survey_options"> %(options)s </div>
  """
  SURVEY_TEMPLATE = """
  <tbody></tbody>
  """

  def __init__(self, *args, **kwargs):
    """Defines the name, key_name and model for this entity."""
    self.this_survey = kwargs.get('this_survey', None)
    if self.this_survey: del kwargs['this_survey']
    super(EditSurvey, self).__init__(*args, **kwargs)

  def render(self, name, value, attrs=None):
    """ Renders the survey editor widget to HTML
    """

    survey = SurveyForm(this_survey=self.this_survey, survey_record=None)
    survey.get_fields()
    if len(survey.fields) == 0: survey = self.SURVEY_TEMPLATE
    options = ""
    for type_id, type_name in self.QUESTION_TYPES.items():
      options += self.BUTTON_TEMPLATE % {'type_id': type_id,
                                         'type_name': type_name}
    options_html = self.OPTIONS_HTML % {'options': options}
    result = self.WIDGET_HTML % {'survey': str(survey),
                                 'options_html':options_html}
    return result


class TakeSurvey(widgets.Widget):
  """Take Survey, or Update Survey.
  """

  WIDGET_HTML = """ %(help_text)s <div class="%(status)s" id="survey_widget">
  <table> %(survey)s </table> </div>
  <script type="text/javascript" src="/soc/content/js/take_survey.js"></script>
  <script type="text/javascript" src="/soc/content/js/jquery.growfield.packed-1.1.js"></script>
  """

  def render(self, this_survey):
    """Renders survey taking widget to HTML.

    Checks if user has already submitted form. If so, show existing form
    If we don't want students/mentors to edit the values they've already
    submitted for a survey, this behavior should be altered.

    (A deadline can also be used as a conditional for updating values,
    and we can just disable the submit button, and add a check on the
    POST handler. )
    """

    user = user_logic.getForCurrentAccount()
    survey_record = SurveyRecord.gql("WHERE user = :1 AND this_survey = :2",
                                     user, this_survey.survey_parent.get()
                                    ).get()
    survey = SurveyForm(this_survey=this_survey, survey_record=survey_record)
    survey.get_fields()
    if survey_record:
      help_text = "Edit and re-submit this survey."
      status = "edit"
    else:
      help_text = "Please complete this survey."
      status = "create"
    result = self.WIDGET_HTML % {'survey': str(survey), 'help_text': help_text,
                                 'status': status}
    return result


class SurveyResults(widgets.Widget):
  """Render List of Survey Results For Given Survey.
  """

  def render(self, this_survey, params, filter=filter, limit=1000, offset=0,
             order=[], idx=0, context={}):
    logic = results_logic
    filter = {'this_survey': this_survey}
    data = logic.getForFields(filter=filter, limit=limit, offset=offset,
                              order=order)

    params['name'] = "Survey Results"
    content = {
      'idx': idx,
      'data': data,
      'logic': logic,
      'limit': limit,
     }
    updates = dicts.rename(params, params['list_params'])
    content.update(updates)
    contents = [content]
    if len(content) == 1:
      content = content[0]
      key_order = content.get('key_order')

    context['list'] = Lists(contents)

    for list in context['list']._contents:
      if len(list['data']) < 1:
        return "<p>No Survey Results Have Been Submitted</p>"
      list['row'] = 'soc/survey/list/results_row.html'
      list['heading'] = 'soc/survey/list/results_heading.html'
      list['description'] = 'Survey Results:'
    context['properties'] = this_survey.this_survey.ordered_properties()
    context['entity_type'] = "Survey Results"
    context['entity_type_plural'] = "Results"
    context['no_lists_msg'] = "No Survey Results"

    markup = loader.render_to_string('soc/survey/results.html',
                                     dictionary=context).strip('\n')
    return markup
