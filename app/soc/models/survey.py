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

"""This module contains the Survey Model.
"""

__authors__ = [
  'JamesLevy" <jamesalexanderlevy@gmail.com>',
]

from google.appengine.ext import db

from django.utils.translation import ugettext

import soc.models.linkable
import soc.models.work
import soc.models.user
import soc.models.student_project

class SurveyContent(db.Expando):
  """Expando Class for Surveys

     Each survey entity consists of properties where names and default
     values are set by the survey creator as survey fields.
  """

  schema = db.TextProperty() # hidden
  created = db.DateTimeProperty(auto_now_add=True)
  modified = db.DateTimeProperty(auto_now=True)

  def set_schema(self, schema):
    self.schema = str(schema)

  def get_schema(self):
    return eval(self.schema)

  def get_survey_order(self):
    survey_order = {}
    schema = self.get_schema()
    for property in self.dynamic_properties():
      # map out the order of the survey fields
      try:
        survey_order[schema[property]["index"]] = property
      except KeyError:
        pass
    return survey_order
    
  def ordered_properties(self):
    properties = []
    survey_order = self.get_survey_order().items()
    for position,key in survey_order:
      properties.insert(position, key)
    return properties 

      
class Survey(soc.models.work.Work):
  """Model of a survey.

  This model describes meta-information and permissions.

  The actual questions of the survey are contained in the SurveyContent entity.
  
  Right now, this model has several properties from Document and it is unclear
  if they are necessary.
  
  The inherited scope property is used to reference to a program.
  Would it be more clear if a 'program' property were used? 
  """

  URL_NAME = 'survey'
  # We should use euphemisms like "student" and "mentor" if possible
  SURVEY_ACCESS = ['admin', 'restricted', 'member', 'user']
  
  
  # These are gsoc specific, so eventually we can subclass this
  SURVEY_TAKING_ACCESS = ['student', 'mentor', 'everyone']
  GRADE_OPTIONS = {
  'midterm':['mid_term_passed', 'mid_term_failed'],
   'final':['final_passed', 'final_failed'], 
   'N/A':[] }
  # there should be a gsoc-specific property determining
  # whether the survey is for the midterm or the final 

  #: field storing the prefix of this document
  # Should this be removed from surveys?
  prefix = db.StringProperty(default='user', required=True,
      choices=['site', 'club', 'sponsor', 'program', 'org', 'user'],
      verbose_name=ugettext('Prefix'))
  prefix.help_text = ugettext(
      'Indicates the prefix of the survey,'
      ' determines which access scheme is used.')

  #: field storing the required access to read this document
  read_access = db.StringProperty(default='restricted', required=True,
      choices=SURVEY_ACCESS,
      verbose_name=ugettext('Survey Read Access'))
  read_access.help_text = ugettext(
      'Indicates who can read the results of this survey.')

  #: field storing the required access to write to this document
  write_access = db.StringProperty(default='admin', required=True,
      choices=SURVEY_ACCESS,
      verbose_name=ugettext('Survey Write Access'))
  write_access.help_text = ugettext(
      'Indicates who can edit this survey.')

  #: field storing the required access to write to this document
  taking_access = db.StringProperty(default='student', required=True,
      choices=SURVEY_TAKING_ACCESS,
      verbose_name=ugettext('Survey Taking Access'))
  taking_access.help_text = ugettext(
      'Indicates who can take this survey.')
      
  #: field storing whether a link to the survey should be featured in
  #: the sidebar menu (and possibly elsewhere); FAQs, Terms of Service,
  #: and the like are examples of "featured" survey
  is_featured = db.BooleanProperty(
      verbose_name=ugettext('Is Featured'))
  is_featured.help_text = ugettext(
      'Field used to indicate if a Work should be featured, for example,'
      ' in the sidebar menu.')

  # deadline for taking survey
  # default should be one week ahead
  deadline = db.DateTimeProperty(required=False)
  deadline.help_text = ugettext(
      'Indicates a date after which this survey'
      ' cannot be taken.')

  has_grades = db.BooleanProperty(
      verbose_name=ugettext('Gradable by mentors'))

  # this property should be named 'survey_content'
  this_survey = db.ReferenceProperty(SurveyContent,
                                     collection_name="survey_parent")


class SurveyRecord(db.Expando):
  """Record produced each time Survey is taken.

  Like SurveyContent, this model includes dynamic properties
  corresponding to the fields of the survey.

  This should also contain a grade value that can be added/edited
  by the administrator of the survey.

  Should this grade value be Binary, String, Integer...?
  """

  this_survey = db.ReferenceProperty(Survey, collection_name="survey_records")
  user = db.ReferenceProperty(reference_class=soc.models.user.User,
                              required=True, collection_name="taken_surveys",
                              verbose_name=ugettext('Created by'))
  project = db.ReferenceProperty(soc.models.student_project.StudentProject, collection_name="survey_records")
  created = db.DateTimeProperty(auto_now_add=True)
  modified = db.DateTimeProperty(auto_now=True)
  grade = db.StringProperty(required=False)

  def get_values(self):
    """Method to get dynamic property values for a survey record.

    Right now it gets all dynamic values, but
    it could also be confined to the SurveyContent entity linked to
    the this_survey entity.
    
    Deprecated Unordered Version
    
    values = []
    for property in self.dynamic_properties():
      values.append(getattr(self, property))
    return values    
    """


  def get_values(self):
    """Method to get dynamic property values for a survey record.

    Right now it gets all dynamic values, but
    it could also be confined to the SurveyContent entity linked to
    the this_survey entity.
    """
    survey_order = self.this_survey.this_survey.get_survey_order()
    values = []
    for position, property in survey_order.items():
        values.insert(position, getattr(self, property, None))
    return values
