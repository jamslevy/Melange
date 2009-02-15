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

"""Seeds or clears the datastore.
"""

__authors__ = [
    '"Sverre Rabbelier" <sverre@rabbelier.nl>',
  ]


import datetime
import itertools

from google.appengine.api import users
from google.appengine.ext import db

from soc.models.site import Site
from soc.models.user import User
from soc.models.sponsor import Sponsor
from soc.models.host import Host
from soc.models.program import Program
from soc.models.timeline import Timeline
from soc.models.org_app import OrgApplication
from soc.models.organization import Organization
from soc.models.org_admin import OrgAdmin
from soc.models.mentor import Mentor
from soc.models.notification import Notification


def seed(*args, **kwargs):
  """Seeds the datastore with some default values.
  """

  account = users.get_current_user()

  if not account:
    account = users.User(email='test@example.com')

  user_properties = {
        'key_name': 'test',
        'link_id': 'test',
        'account': account,
        'agreed_to_tos': True,
        'name': 'Test',
        }

  current_user = User(**user_properties)
  current_user.put()


  group_properties = {
       'key_name': 'google',
       'link_id': 'google',
       'name': 'Google Inc.',
       'short_name': 'Google',
       'founder': current_user,
       'home_page': 'http://www.google.com',
       'email': 'ospo@google.com',
       'description': 'This is the profile for Google.',
       'contact_street': 'Some Street',
       'contact_city': 'Some City',
       'contact_country': 'United States',
       'contact_postalcode': '12345',
       'phone': '1-555-BANANA',
       'status': 'active',
       }

  google = Sponsor(**group_properties)
  google.put()


  role_properties = {
      'key_name': 'google/test',
      'link_id': 'test',
      'scope': google,
      'scope_path': 'google',
      'user': current_user,
      'given_name': 'Test',
      'surname': 'Example',
      'name_on_documents': 'Test Example',
      'email': 'test@example.com',
      'res_street': 'Some Street',
      'res_city': 'Some City',
      'res_state': 'Some State',
      'res_country': 'United States',
      'res_postalcode': '12345',
      'phone': '1-555-BANANA',
      'birth_date': db.DateProperty.now(),
      'agreed_to_tos': True,
      }


  google_host = Host(**role_properties)
  google_host.put()


  timeline_properties = {
        'key_name': 'google/gsoc2009',
        'scope_path': 'google/gsoc2009',
        }

  gsoc2009_timeline = Timeline(**timeline_properties)
  gsoc2009_timeline.put()


  program_properties = {
      'key_name': 'google/gsoc2009',
      'link_id': 'gsoc2009',
      'scope_path': 'google',
      'scope': google,
      'name': 'Google Summer of Code 2009',
      'short_name': 'GSoC 2009',
      'group_label': 'GSOC',
      'description': 'This is the program for GSoC 2009.',
      'apps_tasks_limit': 42,
      'slots': 42,
      'workflow': 'gsoc',
      'timeline': gsoc2009_timeline,
      'status': 'visible',
      }

  gsoc2009 = Program(**program_properties)
  gsoc2009.put()


  org_app_properties = {
    'scope_path': 'google/gsoc2009',
    'scope': gsoc2009,
    'applicant': current_user,
    'home_page': 'http://www.google.com',
    'email': 'org@example.com',
    'description': 'This is an awesome org!',
    'why_applying': 'Because we can',
    'member_criteria': 'They need to be awesome',
    'status': 'pre-accepted',
    'license_name': 'WTFPL',
    'ideas': 'http://code.google.com/p/soc/issues',
    'contrib_disappears': 'We use google to find them',
    'member_disappears': 'See above',
    'encourage_contribs': 'We offer them cookies.',
    'continued_contribs': 'We promise them a cake.',
    'agreed_to_admin_agreement': True,
    }

  for i in range(15):
    org_app_properties['key_name'] = 'google/gsoc2009/org_%d' % i
    org_app_properties['link_id'] = 'org_%d' % i
    org_app_properties['name'] = 'Organization %d' % i
    entity = OrgApplication(**org_app_properties)
    entity.put()


  group_properties.update({
    'key_name': 'google/gsoc2009/melange',
    'link_id': 'melange',
    'name': 'Melange Development Team',
    'short_name': 'Melange',
    'scope_path': 'google/gsoc2009',
    'scope': gsoc2009,
    'home_page': 'http://code.google.com/p/soc',
    'description': 'Melange, share the love!',
    'license_name': 'Apache License',
    'ideas': 'http://code.google.com/p/soc/issues',
    })

  melange = Organization(**group_properties)
  melange.put()


  role_properties.update({
      'key_name': 'google/gsoc2009/melange/test',
      'link_id': 'test',
      'scope_path': 'google/gsoc2009/melange',
      'scope': melange,
      })

  melange_admin = OrgAdmin(**role_properties)
  melange_admin.put()

  melange_mentor = Mentor(**role_properties)
  melange_mentor.put()

  return


def clear(*args, **kwargs):
  """Removes all entities from the datastore.
  """

  entities = itertools.chain(*[
      Notification.all(),
      Mentor.all(),
      OrgAdmin.all(),
      Organization.all(),
      OrgApplication.all(),
      Timeline.all(),
      Program.all(),
      Host.all(),
      Sponsor.all(),
      User.all(),
      Site.all(),
      ])

  for entity in entities:
    entity.delete()

  return

def reseed(*args, **kwargs):
  """Clears and seeds the datastore.
  """

  clear(*args, **kwargs)
  seed(*args, **kwargs)