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

from soc.logic.models import survey
from soc.logic.models import linkable as linkable_logic
from soc.models.work import Work
from soc.models.midterm import Midterm, MidtermRecord

class Logic(survey.Logic):
  """Logic methods for the Midterm Survey model.
  """

  def __init__(self, model=Midterm, base_model=Work,
               scope_logic=linkable_logic):
    """Defines the name, key_name and model for this entity.
    """

    super(Logic, self).__init__(model=model, base_model=base_model,
                                scope_logic=scope_logic)

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
    for name, value in survey_fields.items():
      setattr(survey_record, name, value)
    db.put(survey_record)
    return survey_record

logic = Logic()


class MidtermResultsLogic(survey.Logic):
  """Logic methods for the Survey model
  """

  def __init__(self, model=MidtermRecord,
               base_model=Work, scope_logic=linkable_logic):
    """Defines the name, key_name and model for this entity.
    """

    super(MidtermResultsLogic, self).__init__(model=model, base_model=base_model,
                                scope_logic=scope_logic)

midterm_results_logic = MidtermResultsLogic()
