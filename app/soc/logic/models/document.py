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

"""Document (Model) query functions.
"""

__authors__ = [
  '"Sverre Rabbelier" <sverre@rabbelier.nl>',
  ]


from soc.cache import sidebar
from soc.cache import home
from soc.logic.models import work
from soc.logic.models import linkable as linkable_logic
from soc.logic.models.news_feed import logic as newsfeed_logic
import soc.models.document
import soc.models.work


class Logic(work.Logic):
  """Logic methods for the Document model
  """

  def __init__(self, model=soc.models.document.Document,
               base_model=soc.models.work.Work, scope_logic=linkable_logic):
    """Defines the name, key_name and model for this entity.
    """

    super(Logic, self).__init__(model=model, base_model=base_model,
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


  def getScope(self, entity):
    """Gets Scope for entity.

    params:
      entity = Survey entity
    """

    if getattr(entity, 'scope', None):
      return entity.scope

    import soc.models.program
    import soc.models.organization
    import soc.models.user
    import soc.models.site

    # use prefix to generate dict key
    scope_types = {"program": soc.models.program.Program,
    "org": soc.models.organization.Organization,
    "user": soc.models.user.User,
    "site": soc.models.site.Site}

    # determine the type of the scope
    scope_type = scope_types.get(entity.prefix)

    if not scope_type:
      # no matching scope type found
      raise AttributeError('No Matching Scope type found for %s' % entity.prefix)

    # set the scope and update the entity
    entity.scope = scope_type.get_by_key_name(entity.scope_path)
    entity.put()

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
