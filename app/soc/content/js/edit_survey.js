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


var del_el = "<a class='delete'><img src='/soc/content/images/minus.gif'/></a>";
var del_li = ["<a class='delete_item' id='del_", "' ><img src='/soc/content/images/minus.gif'/></a> "];
var default_option = "<option>" + DEFAULT_OPTION_TEXT + "</option>";    


   $(function(){
   
/*
* == Set Selectors ==
* 
*/

   var widget = $('div#survey_widget');
   widget.parents('td.formfieldvalue:first').css({ 'float': 'left', 
                                                   'width': 200 });



   
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
$('th > label').prepend(del_el).end();

      $('ol').find('li').each(function(){
        $(this).prepend(del_li.join($(this).attr('id'))).end();
      });
 widget.find('.short_answer').each(function(){
 $(this).attr('name', SURVEY_PREFIX + $(this).getPosition() + 'short_answer__' + $(this).attr('name') ) });

 widget.find('.long_answer').each(function(){
 $(this).attr('name', SURVEY_PREFIX + $(this).getPosition() + 'long_answer__' + $(this).attr('name') )
 // TODO: replace scrollbar with jquery autogrow
 .attr('overflow', 'auto'); });
}


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
if (($(this).val().length < 1 || $(this).val() == DEFAULT_SHORT_ANSWER_TEXT) &&
   ($(this).attr('type') != 'hidden')) {
      $(this).preserveDefaultText(DEFAULT_SHORT_ANSWER_TEXT);
}
}); 

widget.find('textarea').each(function(){ 
if ($(this).val().length < 1 | $(this).val() == DEFAULT_LONG_ANSWER_TEXT) $(this).preserveDefaultText(DEFAULT_LONG_ANSWER_TEXT);
$(this).growfield(); // this is resulting in "jittering" behavior

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


// Delete list/choice-field item from survey
widget.find('a.delete_item').click(function(){
    var to_delete = this.id.replace('del_', '');
    $('#delete_item_field').val(to_delete);
    $('#delete_item_dialog').dialog('open');
}).end();




// Add list/choice-field item to survey
$('[name=create-option-button]').each(function() {
      $('#'+ this.id).click(function() {

    $('#new_item_field_ul_id').val($('#' + this.id).parent('fieldset').children('ol').attr('id'));

        $("#new_item_dialog").dialog('open').find('input').focus();
      })
    .hover(
      function(){
        $('#'+ this.id).addClass("ui-state-hover");
      },
      function(){
        $('#'+ this.id).removeClass("ui-state-hover");
      }
    ).mousedown(function(){
      $('#'+ this.id).addClass("ui-state-active");
    })
    .mouseup(function(){
      $('#'+ this.id).removeClass("ui-state-active");
    });
});


options.find('.AddQuestion').click(function(e){
    // Choose a field type
    $("#new_question_button_id").val($(this).attr('id'));
    $("#new_question_dialog").dialog('open').find('input').focus();
  });
  

}).trigger('init');


/* GSOC ROLE-SPECIFIC FIELD PLUGIN
 * Choice between student/mentor renders required GSOC specific fields
 */
 
var taking_access_field = $('select#id_taking_access');
 
taking_access_field.change(function(){
 var role_type = $(this).val();
 addRoleFields(role_type);
	});

 
var addRoleFields = function(role_type){
   // these should ideally be generated with django forms
// TODO: apply info tooltips
var CHOOSE_A_PROJECT_FIELD = '<tr class="role-specific"><th><label>Choose Project:</label></th><td> <select disabled=TRUE id="id_survey__NA__selection__project" name="survey__1__selection__see"><option>Survey Taker\'s Projects For This Program</option></select> </td></tr>';
var CHOOSE_A_GRADE_FIELD =  '<tr class="role-specific"><th><label>Assign Grade:</label></th><td> <select disabled=TRUE id="id_survey__NA__selection__grade" name="survey__1__selection__see"><option>Pass/Fail</option></select> </td></tr>';

  // flush existing role-specific fields
  var role_specific_fields = survey.find('tr.role-specific');
  role_specific_fields.remove();
  
      switch(role_type){
      case "mentor":  
        survey.prepend(CHOOSE_A_GRADE_FIELD);
        survey.prepend(CHOOSE_A_PROJECT_FIELD);
        break;

      case "student": 
        survey.prepend(CHOOSE_A_PROJECT_FIELD);
        break;

   };

};

// run on page load
addRoleFields( taking_access_field.val() );


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


/*
* == Sortable options ==
*/

$(function() {
  $(".sortable").each(function (i, domEle) {
    $('#' + domEle.id).sortable().disableSelection().end();
  });
});

/*
* == Editable options ==
*/

$(function(){
  $('.editable_option').editable({
    editBy: 'dblclick',
    submit: 'change',
    cancel: 'cancel',
    onSubmit: onSubmitEditable,
  });
  function onSubmitEditable(content){
    this;
    alert(this.attr('name'));
    alert(content.current+':'+content.previous)
  }
});






  $(function() {
    
    // Confirmation dialog for deleting list/choice-field item from survey
$("#delete_item_dialog").dialog({
      autoOpen: false,
      bgiframe: true,
      resizable: false,
      height:300,
      modal: true,
      overlay: {
        backgroundColor: '#000',
        opacity: 0.5
      },
      buttons: {
        'Delete this item': function() {
          $('#' + $('#delete_item_field').val()).remove();
          $('#delete_item_field').val('');
          $(this).dialog('close');
        },
        Cancel: function() {
          $('#delete_item_field').val('');
          $(this).dialog('close');
        }
      }
    });


//  Dialog for adding list/choice-field item to survey
    $("#new_item_dialog").dialog({
      bgiframe: true,
      autoOpen: false,
      height: 300,
      modal: true,
      buttons: {
        'Add option': function() {
          var ul_id =  $('#new_item_field_ul_id').val();
          var name = $('#new_item_name').val();
          var i = $('#' + ul_id).find('li').length;
          var id_ = 'id_' + ul_id + '_' + i;
          $('#' + ul_id).append('<li id="id_li_' + name + '_' + i +
              '" class="ui-state-default sortable_li">' +
              '<span class="ui-icon ui-icon-arrowthick-2-n-s"></span>' +
              '<span id="' + id_ + '" class="editable_option" name="'+ id_ +
              '__field">'+ name +'</span>' + '<input type="hidden" id="' +
              id_ + '__field" name="' + id_ + '__field" value="' + name +
              '" >' + '</li>');
          $('#new_item_name').val('');
          $('#new_item_field_ul_id').val('');
          $(this).dialog('close');

        },
        Cancel: function() {
          $('#new_item_name').val('');
          $('#new_item_field_ul_id').val('');
          $(this).dialog('close');
        }
      },
     });
});




$(function() {
//  Dialog for adding new question to survey
  $("#new_question_dialog").dialog({
    bgiframe: true,
    autoOpen: false,
    height: 300,
    modal: true,
    buttons: {
      'Add question': function() {
        var button_id = $("#new_question_button_id").val();
        var survey_table = $('div#survey_widget').find('tbody:first');
        $("#new_question_button_id").val('');
        var field_template =  $("<tr><th><label>" + del_el + "</label></th><td>  </td></tr>");
        var field_name = $("#new_question_name").val();
        if (field_name != '') {
          $("#new_question_name").val('');
          new_field = false;
          var type = button_id + "__";
          // create the HTML for the field
          switch(button_id){
            case "short_answer":
              var new_field = "<input type='text'/ class='short_answer'>";
              break;

            case "long_answer":
              var new_field = "<textarea cols='40' rows='" + min_rows + "' class='long_answer'/>";
              break;

            case "selection":
              var new_field = "<select><option></option>" + default_option + "</select>";
              break;
            case "pick_multi":
              var field_count = survey_table.find('tr').length;
              var new_field_count = field_count + 1 + '__';
              var new_field = "<fieldset class='fieldset'><input type='button' value='" + DEFAULT_OPTION_TEXT + "' /></fieldset>";
              break;
            case "choice":
              var field_count = survey_table.find('tr').length;
              var new_field_count = field_count + 1 + '__';
              var new_field = "<fieldset class='fieldset'><input type='button' value='" + DEFAULT_OPTION_TEXT + "' /></fieldset>";
              break;
            }

          if (new_field) {
            field_count = survey_table.find('tr').length;
            new_field_count = field_count + 1 + '__';
            formatted_name = SURVEY_PREFIX + new_field_count + type +  field_name;
            if (button_id == 'choice')  {
              var name = formatted_name;
              new_field = $('<fieldset>\n  <label for="type_for_' + name +
              '">Question Type</label>' +
              '\n  <select id="type_for_' + name +'" name="type_for_' + name +'">' +
              '\n    <option selected="selected" value="selection">selection</option>' +
              '\n    <option value="pick_multi">pick_multi</option>' +
              '\n  </select>\n  <label for="render_for_' + name + '">Render as</label>' +
              '\n  <select id="render_for_' + name + '" name="render_for_' + name + '">' +
              '\n    <option selected="selected" value="select">select</option>' +
              '\n    <option value="checkboxes">checkboxes</option>'+
              '\n  </select>' +
              '\n  <ol id="' + name + '" class="sortable"></ol>' +
              '\n  <input type="hidden" name="' + name + '" id="id_' + name + '"/>' +
              '\n  <button name="create-option-button" id="create-option-button__' + name +
              '" class="ui-button ui-state-default ui-corner-all" value="' + name +
              '" onClick="return false;">Create new option</button>\n</fieldset>');
            }
            else {
              new_field = $(new_field);
              // maybe the name should be serialized in a more common format
              $(new_field).attr({ 'id': 'id_' + formatted_name, 'name': formatted_name });
            }
            field_template.find('label').attr('for', 'id_' + formatted_name)
            .append(field_name + ":").end().find('td').append(new_field);
            survey_table.append(field_template).trigger('init');
          }
        }
        $(this).dialog('close');
      },
        Cancel: function() {
          $('#new_question_name').val('');
          $("#new_question_button_id").val('')
          $(this).dialog('close');
        }
      },
    });
  });

