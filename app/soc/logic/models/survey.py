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

"""Survey (Model) query functions.
"""

__authors__ = [
  'JamesLevy" <jamesalexanderlevy@gmail.com>',
  ]

from google.appengine.ext import db

from soc.cache import sidebar
from soc.logic.models import work
from soc.logic.models import linkable as linkable_logic
from soc.models.program import Program
from soc.models.survey import SurveyContent, Survey, SurveyRecord
from soc.models.work import Work
from soc.logic.models.news_feed import logic as newsfeed_logic

class Logic(work.Logic):
  """Logic methods for the Survey model.
  """

  def __init__(self, model=Survey, base_model=Work,
               scope_logic=linkable_logic):
    """Defines the name, key_name and model for this entity.
    """

    super(Logic, self).__init__(model=model, base_model=base_model,
                                scope_logic=scope_logic)

  def createSurvey(self, survey_fields, schema, this_survey=False):
    """Create a new survey from prototype.
    """

    if not this_survey:
      this_survey = SurveyContent()
    else:
      # wipe clean existing dynamic properties if they exist
      for prop in this_survey.dynamic_properties():
        delattr(this_survey, prop)
    for name, value in survey_fields.items():
      setattr(this_survey, name, value)
    this_survey.set_schema(schema)
    db.put(this_survey)
    return this_survey

  def updateSurveyRecord(self, user, survey_entity, survey_record, fields):
    """ Create a new survey record, or get an existing one.
    """

    if survey_record:
      for prop in survey_record.dynamic_properties():
        delattr(survey_record, prop)
    else:
      survey_record = SurveyRecord(user=user, this_survey=survey_entity)
    schema = survey_entity.this_survey.get_schema()
    for name, value in fields.items():
      pick_multi = name in schema and schema[name]['type'] == 'pick_multi'
      if pick_multi and hasattr(fields, 'getlist'): # it's a multidict
        setattr(survey_record, name, ','.join(fields.getlist(name)))
      else:
        setattr(survey_record, name, value)
    db.put(survey_record)
    return survey_record


  def getProjects(self, this_survey, user, debug=False):
    """
    Get projects linking user to a program.
    Serves as access handler (since no projects == no access)
    And retrieves projects to choose from (if mentors have >1 projects)

    """
    this_program = this_survey.scope
    from settings import DEBUG as debug 
    if debug:
      user = self.getDebugUser(this_survey, this_program)
    if this_survey.taking_access == 'mentor':
      these_projects = self.getMentorProjects(user, this_program)
    if this_survey.taking_access == 'student':
      these_projects = self.getStudentProjects(user, this_program)
    print ""
    print these_projects
    if len(these_projects) == 0: return False
    return these_projects

  def getDebugUser(self, this_survey, this_program):
    # impersonate another user, for debugging
    if this_survey.taking_access == 'mentor':
      from soc.models.mentor import Mentor
      role = Mentor.get_by_key_name(
      this_program.key().name() + "/org_1/test")
      
    if this_survey.taking_access == 'student':
      from soc.models.student import Student
      role = Student.get_by_key_name(
      this_program.key().name() + "/test")
      print ""
      print role.user.key()
    if role: return role.user

  def getStudentProjects(self, user, program):
      import soc.models.student
      print ""
      print user.key()
      print user.roles.fetch(1000)
      this_student = soc.models.student.Student.all(
      ).filter("user=", user
      ).get()
      print this_student
      if not this_student: return []
      print ""
      print this_student.key
      
      projects = soc.models.student_project.StudentProject.filter(
      "student=", this_student).filter("program=", program).fetch(1000)
      return projects

  def getMentorProjects(self,user, program):
      import soc.models.mentor
      this_mentor = soc.models.mentor.Mentor.all(
      ).filter("user=", user
      ).filter("program=", program
      ).get()
      if not this_mentor: return []
      projects = soc.models.student_project.StudentProject.filter(
      "mentor=", this_mentor).filter("program=", program).fetch(1000)
      return projects

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
