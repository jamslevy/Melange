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

"""This module contains the Midterm subclass for the Survey Model.
"""

__authors__ = [
  'JamesLevy" <jamesalexanderlevy@gmail.com>',
]


from google.appengine.ext import db
import soc.models.survey
import soc.models.student_project

from django.utils.translation import ugettext

import soc.models.linkable
import soc.models.work
import soc.models.user


class Midterm(soc.models.survey.Survey):
  URL_NAME = 'midterm_survey'
  # We should use euphemisms like "student" and "mentor" if possible
  DOCUMENT_ACCESS = ['admin', 'restricted', 'member', 'user']

class MidtermRecord(db.Expando):
  """Should subclass SurveyRecord.
  """

  this_survey = db.ReferenceProperty(Midterm, collection_name="midterm_records")
  project = db.ReferenceProperty(soc.models.student_project.StudentProject,
                                 collection_name="midterms_records")
  grade = db.StringProperty(required=False)

  user = db.ReferenceProperty(reference_class=soc.models.user.User,
                              required=True, collection_name="taken_midterms",
                              verbose_name=ugettext('Created by'))
  created = db.DateTimeProperty(auto_now_add=True)
  modified = db.DateTimeProperty(auto_now=True)

  def get_values(self):
    """Method to get dynamic property values for a survey record.

    Right now it gets all dynamic values, but
    it could also be confined to the SurveyContent entity linked to
    the this_survey entity.
    """

    values = []
    for property in self.dynamic_properties():
      values.append(getattr(self, property))
    return values
