   /* Copyright 2008 the Melange authors.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 * 
 *   http://www.apache.org/licenses/LICENSE-2.0
 * 
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */



var DEFAULT_LONG_ANSWER_TEXT = 'Write a Custom Prompt For This Question...';
var DEFAULT_SHORT_ANSWER_TEXT = 'Write a Custom Prompt For This Question...';
var DEFAULT_OPTION_TEXT = 'Add A New Option...';
var SURVEY_PREFIX = 'survey__';

var min_rows = 10;
max_rows = min_rows * 2;
    
    
    
   $(function(){
   
/*
* == Set Selectors ==
* 
*/

   var widget = $('div#survey_widget');
   widget.parents('td.formfieldvalue:first').css({ 'float': 'left', 
                                                   'width': 200 });


   var del_el = "<a class='delete'><img src='/soc/content/images/minus.gif'/></a>";
   var default_option = "<option>" + DEFAULT_OPTION_TEXT + "</option>";
   
/*
* == Setup for existing surveys ==
* 
*
* 
*/

/*
*  Delete any ghost fields
*  (unable to figure out how to do this serverside since the handler
*  doesn't even get hit sometimes. 
*/

if ( $('input#id_title').val() == '' && $('.formfielderror').length < 1) {
	widget.find('tr').remove();
}
widget.find('table:first').show();

  // Bind submit
/*
*  Restore survey content html from editPost 
*  if POST fails
*/
 
var survey_html = $('form').find("#id_survey_html").attr('value');
if (survey_html && survey_html.length > 1) { 
widget.html(survey_html); // we don't need to re-render HTML

widget.find('textarea,input').each(function(){ 
$(this).val( $(this).attr('val') ); 
}); 
}
else renderHTML();

var survey = widget.find('tbody:first');
var options = widget.find('#survey_options');

   
function renderHTML(){
  // render existing survey forms
widget.find('label').prepend(del_el).end()
      .find('select').append(default_option)
      .each(function(){
      $(this).attr('name', SURVEY_PREFIX + $(this).getPosition() + 'selection__' + $(this).attr('name') ) });

 widget.find('input').each(function(){
 $(this).attr('name', SURVEY_PREFIX + $(this).getPosition() + 'short_answer__' + $(this).attr('name') ) });

 widget.find('textarea').each(function(){
 $(this).attr('name', SURVEY_PREFIX + $(this).getPosition() + 'long_answer__' + $(this).attr('name') )
 // TODO: replace scrollbar with jquery autogrow
 .attr('overflow', 'auto'); });
}


   
options.find('button').click(function(e){
  // Choose a field type
	var field_template =  $("<tr><th><label>" + del_el + "</label></th><td>  </td></tr>");
	var field_name = prompt('Enter a label for this question');
	if (!field_name) return alert('invalid label name');
	new_field = false;
	var type = $(this).attr('id') + "__";

	// create the HTML for the field
	switch($(this).attr('id')){
		case "short_answer":  
			var new_field = "<input type='text'/>";
			break;

		case "long_answer": 
			var new_field = "<textarea cols='40' rows='" + min_rows + "' />";
			break;

		case "selection": 
			var new_field = "<select><option></option>" + default_option + "</select>";
			break;
		case "pick_multi":
			var field_count = survey.find('tr').length;
			var new_field_count = field_count + 1 + '__';
			var new_field = "<fieldset class='fieldset'><input type='button' value='" + DEFAULT_OPTION_TEXT + "' /></fieldset>";
			break;

	}
		if (new_field) {
			
			field_count = survey.find('tr').length;
			new_field_count = field_count + 1 + '__';
			new_field = $(new_field);
			formatted_name = SURVEY_PREFIX + new_field_count + type +  field_name;
			// maybe the name should be serialized in a more common format
			$(new_field).attr({ 'id': 'id_' + formatted_name, 'name': formatted_name });
			field_template.find('label').attr('for', 'id_' + formatted_name)
													 .append(field_name + ":").end()
						  .find('td').append(new_field);
			survey.append(field_template).trigger('init'); 


		}
   });
   
   

/*
* == Initiation ==
* 
* Runs on PageLoad and Each Time Field is Added to Survey
* 
*/
  
survey.bind('init', function(){
  // unnecessarily redundant
  // this should be refactored as a jQuery function that acts on only a single field
  // and it should be merged with renderHTML since they have comparable functionality

widget.find('input').each(function(){ 
if ($(this).val().length < 1 | $(this).val() == DEFAULT_SHORT_ANSWER_TEXT) $(this).preserveDefaultText(DEFAULT_SHORT_ANSWER_TEXT); 
}); 

widget.find('textarea').each(function(){ 
if ($(this).val().length < 1 | $(this).val() == DEFAULT_LONG_ANSWER_TEXT) $(this).preserveDefaultText(DEFAULT_LONG_ANSWER_TEXT);
$(this).growfield(); // this is resulting in "jittering" behavior

}); 

widget.find('select').change(function(){

if ($(this).find('option:selected').text() == DEFAULT_OPTION_TEXT) {
  // create a new option for selection field
var option_name = prompt("Name the new option");
if (option_name == null) return false; if (option_name.length < 1) return false;
$(this).prepend("<option>" + option_name + "</option>").find('option').each(function(){
   if ($(this).val().length < 1) $(this).remove();
}).end().find('option:first').attr('selected', 'selected');

}

});


widget.find(":button").click(function(){
  if ($(this).val() == DEFAULT_OPTION_TEXT){

  var fieldset = $(this).parents('fieldset');
/*  var option_name = prompt("Name the new checkbox");
  if ((option_name == null) || (option_name.length < 1)) {
    return false;
  }*/
  var option_value = prompt("Name the new checkbox");
  if ((option_value == null) || (option_value.length < 1)) {
    return false;
  }

  fieldset.append("<br /><input type='checkbox' checked='checked' value='" + fieldset.attr('id') + "__" + option_value + "' name='" + fieldset.attr('name') + "' >"  + option_value + "</input>").end();

  }
});

widget.find('a.delete img').click(function(){
  // delete a field
	this_field = $(this).parents('tr:first');
    var deleted_id = $(this_field).find('label').attr('for');
delete_this = confirm("Deleting this field will remove all answers submitted for this field. Continue?");
if (delete_this) {
  var edit_form = $('#EditForm');
  var deleted_field = $('#__deleted__');
  if (deleted_field.val()) {
    deleted_field.val(deleted_field.val() + ',' + deleted_id.replace('id_', '')).end();
  }
  else {
    var deleted_input = $("<input type='hidden' value='" + deleted_id.replace('id_', '') + "' />");
    deleted_input.attr({'id':'__deleted__'}).attr({'name':'__deleted__'});
    edit_form.append(deleted_input);
  }
  this_field.remove();
  
}
});



/* GSOC ROLE-SPECIFIC FIELD PLUGIN
 * Choice between student/mentor renders required GSOC specific fields
 */
 
var taking_access_field = $('select#id_taking_access');
 
taking_access_field.change(function(){
 var role_type = $(this).val();
 addRoleFields(role_type);
	});

}).trigger('init');



/*
* == Survey Submission Handler ==
* 
*/

$('form').bind('submit', function(){

/* 
 * get rid of role-specific fields
 */
survey.find('tr.role-specific').remove();
 
/*
 * Save survey content html from editPost 
 * if POST fails
 */
    // save field vals
    widget.find('textarea,input').each(function(){ 
    $(this).attr('val', $(this).val() ); 
    }); 
    
$(this).find("#id_survey_html").attr('value', widget.html());


	// Get all options for select menus
	widget.hide().find('select').each(function(){
		options = Array();
		$(this).find('option').each(function(){
		if ($(this).text() != DEFAULT_OPTION_TEXT) options.push($(this).text());
		});
		$(this).html('').append("<option selected='selected'>" + options + "</option>")
	});
		


	// don't save default value
	widget.find('input').each(function(){ 
	if ( $(this).val() == DEFAULT_SHORT_ANSWER_TEXT) $(this).val('');
	}); 

	// don't save default value
	widget.find('textarea').each(function(){ 
	if ($(this).val() == DEFAULT_LONG_ANSWER_TEXT) $(this).val('');
	}); 

	// get rid of the options
	$('input#id_s_html').val(widget.find('div#survey_options').remove().end().html()); // only needed for HTML

});

  
  
  
   });
   


/*
* == Utils ==
* 
*/

jQuery.fn.extend({

// get position of survey field
getPosition: function(){ 
    var this_row = $(this).parents('tr:first');
    var this_table = this_row.parents('table:first');
    var position = this_table.find('tr').index(this_row) + '__';
    return position;
     }

});





