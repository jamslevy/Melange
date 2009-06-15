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


$(function () {

  /*
  * == Setup Survey on Page Load ==
  *
  */

  var widget = $('div#survey_widget');
  widget.parents('td.formfieldvalue:first').css({
    'float': 'left',
    'width': 200
  });
  var survey = widget.find('tbody:first');

  if (widget.hasClass('create')) {

    /*
    * == Set Custom Field Rules ==
    *
    */
    widget.find('input').each(function () {
      $(this).preserveDefaultText($(this).val());
    });

    widget.find('textarea').each(function () {
      $(this).preserveDefaultText($(this).val()).attr('overflow', 'auto')
      .growfield();
    });

    widget.find('select').change(function () {});

  }

  else {
    widget.find('textarea').each(function () {
      $(this).attr('overflow', 'auto').growfield();
    });
  }
  /*
  * == Survey Submission Handler ==
  *
  */

  $('form').bind('submit', function () {
    $('input#id_s_html').val(
      widget.find('div#survey_options').remove().end().html()
    );
  });
});
