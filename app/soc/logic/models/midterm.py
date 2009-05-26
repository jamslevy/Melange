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

from soc.logic.models import survey, work
from soc.logic.models import linkable as linkable_logic
from soc.models.work import Work
from soc.models.midterm import Midterm, MidtermRecord
from soc.models.survey import SurveyContent

ACLMAP = ['admin', 'restricted', 'mentor', 'student', 'public']

ACLMAP = dict(zip(ACLMAP, ['admin', 'restricted', 'member', 'user', 'public']))

class Logic(work.Logic):
  """Logic methods for the Midterm Survey model.
  """

  def __init__(self, model=Midterm, base_model=Work,
               scope_logic=linkable_logic):
    """Defines the name, key_name and model for this entity.
    """

    super(Logic, self).__init__(model=model, base_model=base_model,
                                scope_logic=scope_logic)

  def create_survey(self, survey_fields, schema, this_survey=False):
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

  def create_survey_record(self, user, survey_entity, survey_fields):
    """ Create a new survey record.
    """

    survey_record = MidtermRecord.gql("WHERE user = :1 AND this_survey = :2",
                                     user, survey_entity).get()
    if survey_record:
      for prop in survey_record.dynamic_properties():
        delattr(survey_record, prop)
    if not survey_record:
      survey_record = MidtermRecord(user = user, this_survey = survey_entity)
    schema = survey_entity.this_survey.get_schema()
    for name, value in survey_fields.items():
      if schema[name]['type'] == 'pick_multi':
        setattr(survey_record, name, ','.join(survey_fields.getlist(name)))
      else:
        setattr(survey_record, name, value)
    db.put(survey_record)
    return survey_record

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


logic = Logic()


class MidtermResultsLogic(work.Logic):
  """Logic methods for the Survey model
  """

  def __init__(self, model=MidtermRecord,
               base_model=Work, scope_logic=linkable_logic):
    """Defines the name, key_name and model for this entity.
    """

    super(MidtermResultsLogic, self).__init__(model=model, base_model=base_model,
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


midterm_results_logic = MidtermResultsLogic()
