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
from soc.logic.models.user import logic as user_logic
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
    self.survey_content = self.kwargs.get('survey_content', None)
    self.this_user = self.kwargs.get('this_user', None)
    self.survey_record = self.kwargs.get('survey_record', None)
    del self.kwargs['survey_content']
    del self.kwargs['this_user']
    del self.kwargs['survey_record']
    super(SurveyForm, self).__init__(*args, **self.kwargs)

  def get_fields(self):
    if not self.survey_content: return
    kwargs = self.kwargs
    self.survey_fields = {}
    schema = self.survey_content.get_schema()
    for property in self.survey_content.dynamic_properties():
      if self.survey_record: # use previously entered value
        value = getattr(self.survey_record, property)
      else: # use prompts set by survey creator
        value = getattr(self.survey_content, property)
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
        options = eval(getattr(self.survey_content, property))
        if self.survey_record:
          these_choices.append((value, value))
          options.remove(value)
        for option in options:
          these_choices.append((option, option))
        self.survey_fields[property] = forms.ChoiceField(choices=tuple(these_choices),
                                              widget=forms.Select())
    return self.insert_fields()

  def insert_fields(self):
    survey_order = self.survey_content.get_survey_order()
    # first, insert dynamic survey fields 
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
  <div class="survey_admin" id="survey_widget"><table> %(survey)s </table> %(options_html)s </div>
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
    self.survey_content = kwargs.get('survey_content', None)
    self.this_user = user_logic.getForCurrentAccount()
    if self.survey_content: del kwargs['survey_content']
    super(EditSurvey, self).__init__(*args, **kwargs)

  def render(self, name, value, attrs=None):
    """ Renders the survey editor widget to HTML
    """

    self.survey_form = SurveyForm(survey_content=self.survey_content, 
    this_user=self.this_user, survey_record=None)
    self.survey_form.get_fields()
    if len(self.survey_form.fields) == 0: self.survey_form = self.SURVEY_TEMPLATE
    options = ""
    for type_id, type_name in self.QUESTION_TYPES.items():
      options += self.BUTTON_TEMPLATE % {'type_id': type_id,
                                         'type_name': type_name}
    options_html = self.OPTIONS_HTML % {'options': options}
    result = self.WIDGET_HTML % {'survey': str(self.survey_form),
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

  def __init__(self, **kwargs):
    self.this_user = kwargs.get('user', None)
    
  def render(self, survey_content, survey_record):
    """Renders survey taking widget to HTML.

    Checks if user has already submitted form. If so, show existing form
    If we don't want students/mentors to edit the values they've already
    submitted for a survey, this behavior should be altered.

    (A deadline can also be used as a conditional for updating values,
    and we can just disable the submit button, and add a check on the
    POST handler. )
    """
    self.survey_content = survey_content
    self.this_survey = self.survey_content.survey_parent.get()
    survey_record = SurveyRecord.gql("WHERE user = :1 AND this_survey = :2",
                                     self.this_user, self.this_survey).get()
    self.survey = SurveyForm(survey_content=survey_content, 
    this_user=self.this_user, survey_record=survey_record)
    self.survey.get_fields()
    self.get_take_survey_fields()
    if survey_record:
      help_text = "Edit and re-submit this survey."
      status = "edit"
    else:
      help_text = "Please complete this survey."
      status = "create"
    result = self.WIDGET_HTML % {'survey': str(self.survey), 'help_text': help_text,
                                 'status': status}
    return result

  def get_take_survey_fields(self):
    # these survey fields are only present when taking the survey
    # check for this program - is this student or a mentor? 
    # I'm assuming for now this is a student -- this should all be refactored as access 
    field_count = len( self.survey.fields.items() )
    these_projects = self.get_projects()
    if not these_projects:
      # failed access check...no relevant project found
      return False     
    project_pairs = []
    for project in these_projects: # gql for this program!
      project_pairs.append((project.key()), (project.title) )
    self.survey.fields.insert(0, 'project', forms.fields.ChoiceField(
    choices=tuple( project_pairs ), widget=forms.Select() )) 
 
    if self.this_user == "mentor":
      # if this is a mentor, add a field 
      # determining if student passes or fails
      # check out GRADE_OPTIONS in Survey model for gsoc-specific
      # choices to offer ('mid_term_passed', etc.)
      self.survey.fields.insert(field_count + 1, 'pass/fail', 
      forms.fields.ChoiceField(choices=('pass','fail'), widget=forms.Select() ) )
      

  def get_projects(self):
    """
    This is a quick attempt to get a working access check,
    and get a list of projects while we're at it.
    
    This method should be migrated to a access module"""
    import soc.models.student_project
    import soc.models.student
    import soc.models.mentor
    import soc.models.program #.Program
    # Get program for survey
    this_program = self.this_survey.scope # or links?
    # this doesn't work because I haven't figured out
    # how to use scope to thread from a survey to its
    # program
    print ""
    print this_program
    # Get role linking survey taker to program
    # we need to make sure we're only getting roles linked to this program
    this_role = self.this_user.roles.filter('scope =', program) #program
    print ""
    print this_role
    # check that the survey_taker has a project with taking_access role type
    # and since mentors can have multiple projects, we're retrieving a list
    # how do we filter on an arbitrary property name?
    """"
    if self.this_survey.taking_access == 'mentor':
       this_project = this_program.student_projects.filter("mentor = :1", this_role)
    """
    # is it better to use filter() or GQL?
    these_projects = soc.models.student_project.StudentProject.gql(
    "WHERE mentor = :1 AND program = :2", this_role, this_program).fetch(1000)
    print ""
    print these_projects
          
      
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
