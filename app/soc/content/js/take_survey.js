

   $(function(){

/*
* == Setup Survey on Page Load ==
*
*/

var widget = $('div#survey_widget');
widget.parents('td.formfieldvalue:first').css({ 'float': 'left',
										   'width': 200 });
var survey = widget.find('tbody:first');

if (widget.hasClass('create')) {

	/*
	* == Set Custom Field Rules ==
	*
	*/


	widget.find('input').each(function(){
	  $(this).preserveDefaultText($(this).val());
	  //.growfield();
	});

	widget.find('textarea').each(function(){
	  $(this).preserveDefaultText($(this).val()).attr('overflow', 'auto');
	  //.growfield();

	});

	widget.find('select').change(function(){});

}

/*
* == Survey Submission Handler ==
*
*/

$('form').bind('submit', function(){
$('input#id_s_html').val(widget.find('div#survey_options').remove().end().html());
});



   });




/*
* == Utils ==
*
*/


jQuery.fn.extend({
preserveDefaultText: function(defaultValue, replaceValue)
{
$(this).focus(function()
{
if(typeof(replaceValue) == 'undefined')
replaceValue = '';
if($(this).val() == defaultValue)
$(this).val(replaceValue);
});

$(this).blur(function(){
if(typeof(replaceValue) == 'undefined')
replaceValue = '';
if($(this).val() == replaceValue)
$(this).val(defaultValue);
});
return $(this).val(defaultValue);
}
});
