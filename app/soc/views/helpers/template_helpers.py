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

"""Helpers for manipulating templates.
"""

__authors__ = [
  '"Todd Larsen" <tlarsen@google.com>',
  ]


def makeSiblingTemplatesList(templates, new_template_file):
  """Converts template paths into a list of "sibling" templates.
  
  Args:
    templates: search list of templates (or just a single template not in a
      list) from which template paths will be extracted (discarding the final
      template file name of each template)
    new_template_file: new "sibling" template file to append to each extracted
      template path
      
  Returns:
    A list of potential "sibling" templates named by new_template_file located
    in the paths of the templates in the supplied list.  For example, from:
      ['foo/bar/the_old_template.html', 'foo/the_old_template.html']
    to:
      ['foo/bar/some_new_template.html', 'foo/some_new_template.html']
  """
  if not isinstance(templates, (list, tuple)):
    templates = [templates]

  return [
      '%s/%s' % (t.rsplit('/', 1)[0], new_template_file) for t in templates]
