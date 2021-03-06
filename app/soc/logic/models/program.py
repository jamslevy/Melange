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

"""Program (Model) query functions.
"""

__authors__ = [
  '"Sverre Rabbelier" <sverre@rabbelier.nl>',
  '"Lennard de Rijk" <ljvderijk@gmail.com>',
  ]


from soc.logic.models import presence_with_tos
from soc.logic.models import sponsor as sponsor_logic

import gsoc.logic.models.timeline
import soc.logic.models.timeline
import soc.models.program


class Logic(presence_with_tos.Logic):
  """Logic methods for the Program model.
  """

  TIMELINE_LOGIC = {'gsoc' : gsoc.logic.models.timeline.logic,
                    'ghop' : soc.logic.models.timeline.logic}

  def __init__(self, model=soc.models.program.Program, 
               base_model=None, scope_logic=sponsor_logic):
    """Defines the name, key_name and model for this entity.
    """

    super(Logic, self).__init__(model=model, base_model=base_model,
                                scope_logic=scope_logic)


logic = Logic()
