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
from django.forms.fields import CharField
from django.template import loader
from django.utils.encoding import force_unicode
from django.utils.html import escape
from django.utils.safestring import mark_safe

from google.appengine.ext.db import djangoforms

from soc.logic import dicts
from soc.logic.lists import Lists
from soc.logic.models.survey import logic as survey_logic, results_logic
from soc.models.survey import SurveyContent


class SurveyForm(djangoforms.ModelForm):
  """Main SurveyContent form.

  This class is used to produce survey forms for several circumstances:
    - Admin creating survey from scratch
    - Admin updating existing survey
    - User taking survey
    - User updating already taken survey

  Using dynamic properties of the survey model (if passed as an arg) the
  survey form is dynamically formed
  """

  def __init__(self, *args, **kwargs):
    """Store special kwargs as attributes.

      read_only: controls whether the survey taking UI allows data entry.
      editing: controls whether to show the edit or show form.
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

    Populates self.survey_fields, which will be ordered in self.insert_fields.
    """

    if not self.survey_content:
      return
    self.survey_fields = {}
    schema = eval(self.survey_content.schema)
    has_record = (not self.editing) and self.survey_record
    extra_attrs = {}

    # Figure out whether we want a read-only view
    if not self.editing:
      # Only survey taking can be read-only
      read_only = self.read_only
      if not read_only:
        deadline = self.survey_content.survey_parent.get().deadline
        read_only =  deadline and (datetime.datetime.now() > deadline)
      if read_only:
        extra_attrs['disabled'] = 'disabled'

    # Add unordered fields to self.survey_fields
    for field in self.survey_content.dynamic_properties():

      if has_record and hasattr(self.survey_record, field):
        # previously entered value
        value = getattr(self.survey_record, field)
      else:
        # use prompts set by survey creator
        value = getattr(self.survey_content, field)

      if field not in schema:
        continue #XXX Should we error here?
      elif 'question' in schema[field]:
        label = schema[field].get('question', None) or field

      # Dispatch to field-specific methods
      if schema[field]["type"] == "long_answer":
        self.addLongField(field, value, extra_attrs, label=label)
      elif schema[field]["type"] == "short_answer":
        self.addShortField(field, value, extra_attrs, label=label)
      elif schema[field]["type"] == "selection":
        self.addSingleField(field, value, extra_attrs, schema, label=label)
      elif schema[field]["type"] == "pick_multi":
        self.addMultiField(field, value, extra_attrs, schema, label=label)
      elif schema[field]["type"] == "pick_quant":
        self.addQuantField(field, value, extra_attrs, schema, label=label)

    return self.insertFields()

  def insertFields(self):
    """Add ordered fields to self.fields.
    """

    survey_order = self.survey_content.getSurveyOrder()
    # first, insert dynamic survey fields
    for position, property in survey_order.items():
      self.fields.insert(position, property, self.survey_fields[property])
    return self.fields

  def addLongField(self, field, value, attrs, req=False, label='', tip=''):
    """Add a long answer fields to this form.
    """

    widget = widgets.Textarea(attrs=attrs)
    if not tip:
      tip = 'Testing Tooltip!'
    question = CharField(help_text=tip, required=req, label=label,
                         widget=widget, initial=value)
    self.survey_fields[field] = question

  def addShortField(self, field, value, attrs, req=False, label='', tip=''):
    """Add a short answer fields to this form.
    """

    attrs['class'] = "text_question"
    widget = widgets.TextInput(attrs=attrs)
    if not tip:
      tip = 'Testing Tooltip!'
    #TODO(ajaksu) max_length should be configurable
    question = CharField(help_text=tip, required=req, label=label,
                         widget=widget, max_length=40, initial=value)
    self.survey_fields[field] = question

  def addSingleField(self, field, value, attrs, schema, req=False, label='',
                     tip=''):
    """Add a selection field to this form.

    Widget depends on whether we're editing or displaying the survey taking UI.
    """
    if self.editing:
      kind = schema[field]["type"]
      render = schema[field]["render"]
      widget = UniversalChoiceEditor(kind, render)
    else:
      widget = WIDGETS[schema[field]['render']](attrs=attrs)
    these_choices = []
    # add all properties, but select chosen one
    options = getattr(self.survey_content, field)
    has_record = not self.editing and self.survey_record
    if has_record and hasattr(self.survey_record, field):
      these_choices.append((value, value))
      if value in options:
        options.remove(value)
    for option in options:
      these_choices.append((option, option))
    if not tip:
      tip = 'Testing Tooltip!'
    question = PickOneField(help_text=tip, required=req, label=label,
                            choices=tuple(these_choices), widget=widget)
    self.survey_fields[field] = question

  def addMultiField(self, field, value, attrs, schema, req=False, label='',
                    tip=''):
    """Add a pick_multi field to this form.

    Widget depends on whether we're editing or displaying the survey taking UI.
    """

    if self.editing:
      kind = schema[field]["type"]
      render = schema[field]["render"]
      widget = UniversalChoiceEditor(kind, render)
    else:
      widget = WIDGETS[schema[field]['render']](attrs=attrs)
    if self.survey_record and isinstance(value, basestring):
      #TODO(ajaksu) Need to allow checking checkboxes by default
      # Pass as 'initial' so MultipleChoiceField can render checked boxes
      value = value.split(',')
    else:
      value = None
    these_choices = [(v,v) for v in getattr(self.survey_content, field)]
    if not tip:
      tip = 'Testing Tooltip for Multiple Choices!'
    question = PickManyField(help_text=tip, required=req, label=label,
                             choices=tuple(these_choices), widget=widget,
                             initial=value)
    self.survey_fields[field] = question

  def addQuantField(self, field, value, attrs, schema, req=False, label='',
                    tip=''):
    """Add a pick_quant field to this form.

    Widget depends on whether we're editing or displaying the survey taking UI.
    """

    if self.editing:
      kind = schema[field]["type"]
      render = schema[field]["render"]
      widget = UniversalChoiceEditor(kind, render)
    else:
      widget = WIDGETS[schema[field]['render']](attrs=attrs)
    if self.survey_record:
      value = value
    else:
      value = None
    these_choices = [(v,v) for v in getattr(self.survey_content, field)]
    if not tip:
      tip = 'Testing Tooltip for Multiple Choices!'
    question = PickQuantField(help_text=tip, required=req, label=label,
                             choices=tuple(these_choices), widget=widget,
                             initial=value)
    self.survey_fields[field] = question

  class Meta(object):
    model = SurveyContent
    exclude = ['schema']


class UniversalChoiceEditor(widgets.Widget):
  """Edit interface for choice questions.

  Allows adding and removing options, re-ordering and editing option text.
  """

  # Template for each option
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
  # Question type drop-down
  TYPE_TPL = '''
  <label for="type_for_%(name)s">Question Type</label>
  <select id="type_for_%(name)s" name="type_for_%(name)s">
    <option value="selection" %(is_selection)s>selection</option>
    <option value="pick_multi" %(is_pick_multi)s>pick_multi</option>
    <option value="pick_quant" %(is_pick_quant)s>pick_quant</option>
  </select>
  '''
  # Render widget drop-down
  RENDER_TPL = '''
  <label for="render_for_%(name)s">Render as</label>
  <select id="render_for_%(name)s" name="render_for_%(name)s">
    <option value="select" %(is_select)s>select</option>
    <option value="checkboxes" %(is_checkboxes)s>checkboxes</option>
    <option value="radio_buttons" %(is_radio_buttons)s>radio_buttons</option>
  </select>
  '''
  # Each choice field has a hidden input where its 'question' is stored.
  # Open the ordered list.
  HEADER_TPL = '''
  <input type="hidden" id="order_for_%(name)s"
  name="order_for_%(name)s" value=""/>
  <ol id="%(name)s" class="sortable">
  '''
  # Close the ordered list and add the 'add option' button.
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
    if value is None:
      value = ''
    final_attrs = self.build_attrs(attrs, name=name)
    selected = 'selected="selected"'
    # Find out which options should be selected in type and render drop-downs.
    render_kind =  dict(
        name=name,
        is_selection=selected * (self.kind == 'selection'),
        is_pick_multi=selected * (self.kind == 'pick_multi'),
        is_pick_quant=selected * (self.kind == 'pick_quant'),
        is_select=selected * (self.render_as == 'single_select'),
        is_checkboxes=selected * (self.render_as == 'multi_checkbox'),
        is_radio_buttons=selected * (self.render_as == 'quant_radio'),
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
  """Stub for customizing the single choice field.
  """

  def __init__(self, *args, **kwargs):
    super(PickOneField, self).__init__(*args, **kwargs)


class PickManyField(forms.MultipleChoiceField):
  """Stub for customizing the multiple choice field.
  """

  def __init__(self, *args, **kwargs):
    super(PickManyField, self).__init__(*args, **kwargs)


class PickQuantField(forms.MultipleChoiceField):
  """Stub for customizing the multiple choice field.
  """

  def __init__(self, *args, **kwargs):
    super(PickQuantField, self).__init__(*args, **kwargs)


class PickOneSelect(forms.Select):
  """Stub for customizing the single choice select widget.
  """

  def __init__(self, *args, **kwargs):
    super(PickOneSelect, self).__init__(*args, **kwargs)


class PickManyCheckbox(forms.CheckboxSelectMultiple):
  """Customized multiple choice checkbox widget.
  """

  def __init__(self, *args, **kwargs):
    super(PickManyCheckbox, self).__init__(*args, **kwargs)

  def render(self, name, value, attrs=None, choices=()):
    """Render checkboxes as list items grouped in a fieldset.

    This is the pick_multi widget for survey taking
    """

    if value is None:
      value = []
    has_id = attrs and attrs.has_key('id')
    final_attrs = self.build_attrs(attrs, name=name)
    # Normalize to strings.
    str_values = set([forms.util.smart_unicode(v) for v in value])
    is_checked = lambda value: value in str_values
    smart_unicode = forms.util.smart_unicode

    # Set container fieldset and list
    output = [u'<fieldset id="id_%s">\n  <ul class="pick_multi">' % name]

    # Add numbered checkboxes wrapped in list items
    chained_choices = enumerate(chain(self.choices, choices))
    for i, (option_value, option_label) in chained_choices:
      option_label = escape(smart_unicode(option_label))
      # If an ID attribute was given, add a numeric index as a suffix,
      # so that the checkboxes don't all have the same ID attribute.
      if has_id:
        final_attrs = dict(final_attrs, id='%s_%s' % (attrs['id'], i))

      cb = widgets.CheckboxInput(final_attrs, check_test=is_checked)
      rendered_cb = cb.render(name, option_value)
      cb_label = (rendered_cb, option_label)

      output.append(u'    <li><label>%s %s</label></li>' % cb_label)

    output.append(u'  </ul>\n</fieldset>')
    return u'\n'.join(output)

  def id_for_label(self, id_):
    # See the comment for RadioSelect.id_for_label()
    if id_:
      id_ += '_fieldset'
    return id_
  id_for_label = classmethod(id_for_label)


class PickQuantRadioRenderer(widgets.RadioFieldRenderer):
  """Used by PickQuantRadio to enable customization of radio widgets.
  """

  def __init__(self, *args, **kwargs):
    super(PickQuantRadioRenderer, self).__init__(*args, **kwargs)

  def render(self):
    """Outputs a <ul> for this set of radio fields.
    """

    return mark_safe(u'<div class="quant_radio">\n%s\n</div>'
                     % u'\n'.join([u'%s' % force_unicode(w) for w in self]))


class PickQuantRadio(forms.RadioSelect):

  renderer = PickQuantRadioRenderer

  def __init__(self, *args, **kwargs):
    super(PickQuantRadio, self).__init__(*args, **kwargs)


# In the future, we'll have more widget types here
WIDGETS = {'multi_checkbox': PickManyCheckbox,
           'single_select': PickOneSelect,
           'quant_radio': PickQuantRadio}


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

    #TODO(ajaksu) Is this the best way to build the results list?
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







def getRoleSpecificFields(survey, user, survey_form, survey_record):
  # Serves as both access handler and retrieves projects for selection
  from django import forms
  field_count = len(eval(survey.survey_content.schema).items())
  these_projects = survey_logic.getProjects(survey, user)
  if not these_projects: return False # no projects found

  project_pairs = []
  #insert a select field with options for each project
  for project in these_projects:
    project_pairs.append((project.key(), project.title))
  if project_pairs:
    project_tuples = tuple(project_pairs)
    # add select field containing list of projects
    projectField =  forms.fields.ChoiceField(
                              choices=project_tuples,
                              required=True,
                              widget=forms.Select())
    projectField.choices.insert(0, (None, "Choose a Project")  )
    if survey_record:
      for tup in project_tuples:
        if tup[1] == survey_record.project.title:
          projectField.choices.insert(0, (tup[0],tup[1] + " (Saved)")  )
          projectField.choices.remove(tup)
          break;


    survey_form.fields.insert(0, 'project', projectField )

  if survey.taking_access == "mentor":
    # if this is a mentor, add a field
    # determining if student passes or fails
    # Activate grades handler should determine whether new status
    # is midterm_passed, final_passed, etc.
    grade_choices = (('pass', 'Pass'), ('fail', 'Fail'))
    grade_vals = { 'pass': True, 'fail': False }
    gradeField = forms.fields.ChoiceField(choices=grade_choices,
                                           required=True,
                                           widget=forms.Select())

    gradeField.choices.insert(0, (None, "Choose a Grade")  )
    if survey_record:
      for g in grade_choices:
        if grade_vals[g[0]] == survey_record.grade:
          gradeField.choices.insert(0, (g[0],g[1] + " (Saved)")   )
          gradeField.choices.remove(g)
          break;
      gradeField.show_hidden_initial = True

    survey_form.fields.insert(field_count + 1, 'grade', gradeField)

  return survey_form
