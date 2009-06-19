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

"""Survey (Model) query functions.
"""

__authors__ = [
  '"Daniel Diniz" <ajaksu@gmail.com>',
  '"James Levy" <jamesalexanderlevy@gmail.com>',
  ]

import logging

from google.appengine.ext import db

import soc.models.student_project

from soc.cache import sidebar
from soc.logic.models import work
from soc.logic.models import linkable as linkable_logic
from soc.models.program import Program
from soc.models.survey import SurveyContent, Survey
from soc.models.survey_record import SurveyRecord
from soc.models.work import Work
from soc.logic.models.news_feed import logic as newsfeed_logic
from soc.logic.models.user import logic as user_logic


GRADES = {'pass': True, 'fail': False}


class Logic(work.Logic):
  """Logic methods for the Survey model.
  """

  def __init__(self, model=Survey, base_model=Work,
               scope_logic=linkable_logic):
    """Defines the name, key_name and model for this entity.
    """

    super(Logic, self).__init__(model=model, base_model=base_model,
                                scope_logic=scope_logic)

  def createSurvey(self, survey_fields, schema, survey_content=False):
    """Create a new survey from prototype.
    """

    if not survey_content:
      survey_content = SurveyContent()
    else:
      # wipe clean existing dynamic properties if they exist
      for prop in survey_content.dynamic_properties():
        delattr(survey_content, prop)
    for name, value in survey_fields.items():
      setattr(survey_content, name, value)
    survey_content.schema = str(schema)
    db.put(survey_content)
    return survey_content

  def updateSurveyRecord(self, user, survey_entity, survey_record, fields):
    """ Create a new survey record, or get an existing one.
    """

    if survey_record:
      for prop in survey_record.dynamic_properties():
        delattr(survey_record, prop)
    else:
      survey_record = SurveyRecord(user=user, survey=survey_entity)
    schema = eval(survey_entity.survey_content.schema)
    for name, value in fields.items():
      if name == 'project':
        project = soc.models.student_project.StudentProject.get(value)
        survey_record.project = project
      elif name == 'grade':
        survey_record.grade = GRADES[value]
      else:
        pick_multi = name in schema and schema[name]['type'] == 'pick_multi'
        if pick_multi and hasattr(fields, 'getlist'): # it's a multidict
          setattr(survey_record, name, ','.join(fields.getlist(name)))
        else:
          setattr(survey_record, name, value)
    db.put(survey_record)
    return survey_record

  def getKeyNameFromPath(self, path):
    """ Gets survey key name from a request path
    """
    return '/'.join(path.split('/')[-4:]).split('?')[0]


  def getProjects(self, survey, user, debug=False):
    """
    Get projects linking user to a program.
    Serves as access handler (since no projects == no access)
    And retrieves projects to choose from (if mentors have >1 projects)

    """
    this_program = survey.scope
    from settings import DEBUG as debug
    if debug:
      user = self.getDebugUser(survey, this_program)
    if survey.taking_access == 'mentor':
      these_projects = self.getMentorProjects(user, this_program)
    if survey.taking_access == 'student':
      these_projects = self.getStudentProjects(user, this_program)
    if len(these_projects) == 0:
      return False
    return these_projects

  def getDebugUser(self, survey, this_program):
    # impersonate another user, for debugging
    if survey.taking_access == 'mentor':
      from soc.models.mentor import Mentor
      role = Mentor.get_by_key_name(
      this_program.key().name() + "/org_1/test")

    if survey.taking_access == 'student':
      from soc.models.student import Student
      role = Student.get_by_key_name(
      this_program.key().name() + "/test")
    if role: return role.user

  def getStudentProjects(self, user, program):
      import soc.models.student
      from soc.logic.models.student import logic as student_logic
      user_students = student_logic.getForFields({'user': user}) # status=active?
      if not user_students: return []
      return [project for project in sum((list(u.student_projects.run()
      ) for u in user_students), []
      ) if project.program.key() == program.key()]


  def getMentorProjects(self, user, program):
      import soc.models.mentor
      from soc.logic.models.mentor import logic as mentor_logic
      user_mentors = mentor_logic.getForFields({'user': user}) # program = program  # status=active?
      if not user_mentors: return []
      return [project for project in sum((list(u.student_projects.run()
      ) for u in user_mentors), []
      ) if project.program.key() == program.key()]

  def getKeyValuesFromEntity(self, entity):
    """See base.Logic.getKeyNameValues.
    """

    return [entity.prefix, entity.scope_path, entity.link_id]

  def getKeyValuesFromFields(self, fields):
    """See base.Logic.getKeyValuesFromFields.
    """

    return [fields['prefix'], fields['scope_path'], fields['link_id']]

  def getKeyFieldNames(self):
    """See base.Logic.getKeyFieldNames.
    """

    return ['prefix', 'scope_path', 'link_id']

  def isDeletable(self, entity):
    """See base.Logic.isDeletable.
    """

    return not entity.home_for

  def _updateField(self, entity, entity_properties, name):
    """Special logic for role.

    If state changes to active we flush the sidebar.
    """

    value = entity_properties[name]
    if (name == 'is_featured') and (entity.is_featured != value):
      sidebar.flush()
    return True


  def getScope(self, entity):
    """gets Scope for entity
    """
    if getattr(entity, 'scope', None): return entity.scope
    import soc.models.program
    import soc.models.organization
    import soc.models.user
    import soc.models.site
    # anything else?
    # use prefix to generate dict key
    scope_types = {"program": soc.models.program.Program,
    "org": soc.models.organization.Organization,
    "user": soc.models.user.User,
    "site": soc.models.site.Site}
    scope_type = scope_types.get(entity.prefix)
    if not scope_type: raise AttributeError
    entity.scope = scope_type.get_by_key_name(entity.scope_path)
    entity.put()
    return entity.scope

  def _onCreate(self, entity):
    self.getScope(entity)
    receivers = [entity.scope]
    newsfeed_logic.addToFeed(entity, receivers, "created")


  def _onUpdate(self, entity):
    self.getScope(entity) # for older entities
    receivers = [entity.scope]
    newsfeed_logic.addToFeed(entity, receivers, "updated")


  def _onDelete(self, entity):
    receivers = [entity.scope]
    newsfeed_logic.addToFeed(entity, receivers, "deleted")


logic = Logic()


def getRoleSpecificFields(survey, user, survey_form):
  # Serves as both access handler and retrieves projects for selection
  from django import forms
  field_count = len(eval(survey.survey_content.schema).items())
  these_projects = logic.getProjects(survey, user)
  if not these_projects: return False # no projects found

  project_pairs = []
  #insert a select field with options for each project
  for project in these_projects:
    project_pairs.append((project.key(), project.title))
  if project_pairs:
    # add select field containing list of projects
    survey_form.fields.insert(0, 'project',
                            forms.fields.ChoiceField(
                                choices=tuple(project_pairs),
                                widget=forms.Select())
                            )
  if survey.taking_access == "mentor":
    # if this is a mentor, add a field
    # determining if student passes or fails
    # Activate grades handler should determine whether new status
    # is midterm_passed, final_passed, etc.
    choices = (('pass', 'pass'), ('fail', 'fail'))
    grade_field = forms.fields.ChoiceField(choices=choices,
                                           widget=forms.Select())
    survey_form.fields.insert(field_count + 1, 'grade', grade_field)

  return survey_form


class ResultsLogic(work.Logic):
  """Logic methods for the Survey model
  """

  def __init__(self, model=SurveyRecord,
               base_model=Work, scope_logic=linkable_logic):
    """Defines the name, key_name and model for this entity.
    """

    super(ResultsLogic, self).__init__(model=model, base_model=base_model,
                                scope_logic=scope_logic)

  def getKeyValuesFromEntity(self, entity):
    """See base.Logic.getKeyNameValues.
    """

    return [entity.prefix, entity.scope_path, entity.link_id]

  def getKeyValuesFromFields(self, fields):
    """See base.Logic.getKeyValuesFromFields.
    """

    return [fields['prefix'], fields['scope_path'], fields['link_id']]

  def getKeyFieldNames(self):
    """See base.Logic.getKeyFieldNames.
    """

    return ['prefix', 'scope_path', 'link_id']

  def isDeletable(self, entity):
    """See base.Logic.isDeletable.
    """

    return not entity.home_for

  def _updateField(self, entity, entity_properties, name):
    """Special logic for role. If state changes to active we flush the sidebar.
    """

    value = entity_properties[name]

    if (name == 'is_featured') and (entity.is_featured != value):
      sidebar.flush()

    home_for = entity.home_for
    if (name != 'home_for') and home_for:
      home.flush(home_for)
    return True


results_logic = ResultsLogic()
