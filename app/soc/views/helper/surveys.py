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

"""Custom widgets used for Survey form fields, plus the SurveyContent form.
"""

__authors__ = [
  '"Daniel Diniz" <ajaksu@gmail.com>',
  '"James Levy" <jamesalexanderlevy@gmail.com>',
  ]


import datetime
from itertools import chain

from django import forms
from django.forms import widgets
from django.template import loader
from django.utils.html import escape

from google.appengine.ext.db import djangoforms

from soc.logic import dicts
from soc.logic.lists import Lists
from soc.logic.models.survey import results_logic
from soc.models.survey import SurveyContent


class SurveyForm(djangoforms.ModelForm):
  def __init__(self, *args, **kwargs):
    """ This class is used to produce survey forms for several
    circumstances:

    - Admin creating survey from scratch
    - Admin updating existing survey
    - User taking survey
    - User updating already taken survey

    Using dynamic properties of the survey model (if passed
    as an arg) the survey form is dynamically formed.

    """

    self.kwargs = kwargs
    self.survey_content = self.kwargs.get('survey_content', None)
    self.this_user = self.kwargs.get('this_user', None)
    self.survey_record = self.kwargs.get('survey_record', None)
    del self.kwargs['survey_content']
    del self.kwargs['this_user']
    del self.kwargs['survey_record']
    self.read_only = self.kwargs.get('read_only', None)
    if 'read_only' in self.kwargs:
      del self.kwargs['read_only']
    self.editing = self.kwargs.get('editing', None)
    if 'editing' in self.kwargs:
      del self.kwargs['editing']

    super(SurveyForm, self).__init__(*args, **self.kwargs)

  def getFields(self):
    """Build the SurveyContent (questions) form fields.
    """

    if not self.survey_content: return
    extra_attrs = {}
    if not self.editing:
      read_only = self.read_only
      if not read_only:
        deadline = self.survey_content.survey_parent.get().deadline
        read_only =  deadline and (datetime.datetime.now() > deadline)
      if read_only:
        extra_attrs['disabled'] = 'disabled'
    kwargs = self.kwargs
    self.survey_fields = {}
    schema = eval(self.survey_content.schema)
    has_record = (not self.editing) and self.survey_record
    for property in self.survey_content.dynamic_properties():
      if has_record and hasattr(self.survey_record, property):
        # use previously entered value
        value = getattr(self.survey_record, property)
      else: # use prompts set by survey creator
        value = getattr(self.survey_content, property)
      if property not in schema: continue
      # correct answers? Necessary for grading
      if 'question' in schema[property]:
        label = schema[property]['question']
      else:
        label = property
      if schema[property]["type"] == "long_answer":
        self.survey_fields[property] = forms.fields.CharField(
                                    help_text = 'Testing Tooltip!',
                                    required=False,
                                    label=label,
                                    widget=widgets.Textarea(attrs=extra_attrs),
                                    initial=value,
                                    )
      if schema[property]["type"] == "short_answer":
        extra_attrs['class'] = "text_question"
        self.survey_fields[property] = forms.fields.CharField(
                                    help_text = 'Testing Tooltip Again!',
                                    required=False,
                                    label=label,
                                    widget=widgets.TextInput(attrs=extra_attrs),
                                    max_length=40,
                                    initial=value,
                                    )
      if schema[property]["type"] == "selection":
        if self.editing:
          kind = schema[property]["type"]
          render = schema[property]["render"]
          widget = UniversalChoiceEditor(kind, render)
        else:
          widget = WIDGETS[schema[property]['render']](attrs=extra_attrs)
        these_choices = []
        # add all properties, but select chosen one
        options = getattr(self.survey_content, property)
        if self.survey_record and hasattr(self.survey_record, property):
          these_choices.append((value, value))
          if value in options:
            options.remove(value)
        for option in options:
          these_choices.append((option, option))
        self.survey_fields[property] = PickOneField(
            help_text = 'Testing Tooltip for Selects!',
            required=False,
            label=label,
            choices=tuple(these_choices),
            widget=widget)
      if schema[property]["type"] == "pick_multi":
        if self.editing:
          kind = schema[property]["type"]
          render = schema[property]["render"]
          widget = UniversalChoiceEditor(kind, render)
        else:
          widget = WIDGETS[schema[property]['render']](attrs=extra_attrs)
        if self.survey_record and isinstance(value, basestring):
          #XXX Need to allow checking checkboxes by default
          # Pass as 'initial' so MultipleChoiceField can render checked boxes
          value = value.split(',')
        else:
          value = None
        these_choices = [(v,v) for v in getattr(self.survey_content, property)]
        self.survey_fields[property] = PickManyField(
            help_text = 'Testing Tooltip for Checkboxes!',
            required=False,
            label=label,
            choices=tuple(these_choices),
            widget=widget,
            initial=value,
            )

    return self.insertFields()

  def insertFields(self):
    survey_order = self.survey_content.getSurveyOrder()
    # first, insert dynamic survey fields
    for position, property in survey_order.items():
      self.fields.insert(position, property, self.survey_fields[property])
    return self.fields

  class Meta(object):
    model = SurveyContent
    exclude = ['schema']


class UniversalChoiceEditor(widgets.Widget):
  CHOICE_TPL = u'''
    <li id="id-li-%(name)s_%(i)s" class="ui-state-default sortable_li">
      <span class="ui-icon ui-icon-arrowthick-2-n-s"></span>
      <span id="%(id_)s" class="editable_option" name="(id_)s__field">
        %(o_val)s
      </span>
      <input type="hidden" id="%(id_)s__field"
       name="%(id_)s__field" value="%(o_val)s"/>
    </li>
  '''

  TYPE_TPL = '''
  <label for="type_for_%(name)s">Question Type</label>
  <select id="type_for_%(name)s" name="type_for_%(name)s">
    <option value="selection" %(is_selection)s>selection</option>
    <option value="pick_multi" %(is_pick_multi)s>pick_multi</option>
  </select>
  '''

  RENDER_TPL = '''
  <label for="render_for_%(name)s">Render as</label>
  <select id="render_for_%(name)s" name="render_for_%(name)s">
    <option value="select" %(is_select)s>select</option>
    <option value="checkboxes" %(is_checkboxes)s>checkboxes</option>
  </select>
  '''

  HEADER_TPL = '''
  <input type="hidden" id="order_for_%(name)s"
  name="order_for_%(name)s" value=""/>
  <ol id="%(name)s" class="sortable">
  '''

  BUTTON_FOOTER = '''
  </ol>
  <button name="create-option-button" id="create-option-button__%(name)s"
   class="ui-button ui-state-default ui-corner-all" value="%(name)s"
   onClick="return false;">Create new option</button>
   \n</fieldset>
  '''

  def __init__(self, kind, render, attrs=None, choices=()):
    self.attrs = attrs or {}
    # choices can be any iterable, but we may need to render this widget
    # multiple times. Thus, collapse it into a list so it can be consumed
    # more than once.
    self.choices = list(choices)
    self.kind = kind
    self.render_as = render

  def render(self, name, value, attrs=None, choices=()):
    if value is None: value = ''
    final_attrs = self.build_attrs(attrs, name=name)
    selected = 'selected="selected"'
    render_kind =  dict(
        name=name,
        is_selection=selected * (self.kind == 'selection'),
        is_pick_multi=selected * (self.kind == 'pick_multi'),
        is_select=selected * (self.render_as == 'single_select'),
        is_checkboxes=selected * (self.render_as == 'multi_checkbox'),
        )
    output = [u'<fieldset>']
    output.append(self.TYPE_TPL %  render_kind)
    output.append(self.RENDER_TPL % render_kind)
    output.append(self.HEADER_TPL % render_kind)
    str_value = forms.util.smart_unicode(value) # Normalize to string.
    chained_choices = enumerate(chain(self.choices, choices))
    id_ = 'id_%s_%s'
    for i, (option_value, option_label) in chained_choices:
      tmp = []
      option_value = escape(forms.util.smart_unicode(option_value))
      vals = dict(id_= id_ % (name, i), name=name, i=i, o_val=option_value)
      output.append(self.CHOICE_TPL % vals)
    output.append(self.BUTTON_FOOTER % render_kind)
    return u'\n'.join(output)

class PickOneField(forms.ChoiceField):

  def __init__(self, *args, **kwargs):
    super(PickOneField, self).__init__(*args, **kwargs)


class PickManyField(forms.MultipleChoiceField):

  def __init__(self, *args, **kwargs):
    super(PickManyField, self).__init__(*args, **kwargs)


class PickOneSelect(forms.Select):

  def __init__(self, *args, **kwargs):
    super(PickOneSelect, self).__init__(*args, **kwargs)


class PickManyCheckbox(forms.CheckboxSelectMultiple):

  def __init__(self, *args, **kwargs):
    super(PickManyCheckbox, self).__init__(*args, **kwargs)

  def render(self, name, value, attrs=None, choices=()):
    if value is None: value = []
    has_id = attrs and attrs.has_key('id')
    final_attrs = self.build_attrs(attrs, name=name)
    output = [u'<fieldset id="id_%s">\n  <ul class="pick_multi">' % name]
    # Normalize to strings.
    str_values = set([forms.util.smart_unicode(v) for v in value])
    chained_choices = enumerate(chain(self.choices, choices))
    for i, (option_value, option_label) in chained_choices:
      # If an ID attribute was given, add a numeric index as a suffix,
      # so that the checkboxes don't all have the same ID attribute.
      if has_id:
        final_attrs = dict(final_attrs, id='%s_%s' % (attrs['id'], i))
      cb = widgets.CheckboxInput(final_attrs,
                                 check_test=lambda value: value in str_values)
      option_value = forms.util.smart_unicode(option_value)
      rendered_cb = cb.render(name, option_value)
      cb_label = (rendered_cb, escape(forms.util.smart_unicode(option_label)))
      output.append(u'    <li><label>%s %s</label></li>' % cb_label)
    output.append(u'  </ul>\n</fieldset>')
    return u'\n'.join(output)

  def id_for_label(self, id_):
    # See the comment for RadioSelect.id_for_label()
    if id_:
      id_ += '_fieldset'
    return id_
  id_for_label = classmethod(id_for_label)


WIDGETS = {'multi_checkbox': PickManyCheckbox,
           'single_select': PickOneSelect}


class SurveyResults(widgets.Widget):
  """Render List of Survey Results For Given Survey.
  """

  def render(self, survey, params, filter=filter, limit=1000, offset=0,
             order=[], idx=0, context={}):
    logic = results_logic
    filter = {'survey': survey}
    data = logic.getForFields(filter=filter, limit=limit, offset=offset,
                              order=order)

    params['name'] = "Survey Results"

    content = {
      'idx': idx,
      'data': data,
      'logic': logic,
      'limit': limit,
     }
    updates = dicts.rename(params, params['list_params'])
    content.update(updates)
    contents = [content]
    if len(content) == 1:
      content = content[0]
      key_order = content.get('key_order')

    context['list'] = Lists(contents)

    for list_ in context['list']._contents:
      if len(list_['data']) < 1:
        return "<p>No Survey Results Have Been Submitted</p>"
      list_['row'] = 'soc/survey/list/results_row.html'
      list_['heading'] = 'soc/survey/list/results_heading.html'
      list_['description'] = 'Survey Results:'
    context['properties'] = survey.survey_content.orderedProperties()
    context['entity_type'] = "Survey Results"
    context['entity_type_plural'] = "Results"
    context['no_lists_msg'] = "No Survey Results"
    context['grades'] = survey.has_grades
    path = (survey.entity_type().lower(), survey.prefix,
            survey.scope_path, survey.link_id)
    context['grade_action'] = "/%s/grade/%s/%s/%s" % path

    markup = loader.render_to_string('soc/survey/results.html',
                                     dictionary=context).strip('\n')
    return markup
