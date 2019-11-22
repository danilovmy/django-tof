/*
* @Author: MaxST
* @Date:   2019-11-09 13:52:25
* @Last Modified by:   MaxST
* @Last Modified time: 2019-11-22 13:04:18
*/
(function ($) {
  'use strict';
  window.generic_view_json = function (fields, text) {
    var $drop = $('#id_name');
    var $select = $drop;
    var value = $drop.val();
    if (! $select.parent().is(".related-widget-wrapper")) {
      $select = $('<div class="related-widget-wrapper"/>');
      $drop.replaceWith($select);
    } else {
      $select = $select.parent();
    }
    var sel = $('<select/>');
    sel.attr({
      'id': 'id_name',
      'name': 'name',
      'class': 'admin-autocomplete',
      'tabindex': -1,
      'data-allow-clear': false,
      'data-placeholder': '',
      'data-theme': 'admin-autocomplete'
    });
    var data = [];
    $.each(fields, function (index, field) {
      var selected = '';
      if (field == value) {
        selected = 'selected';
      }
      sel.append('<option value="' + field + '" ' + selected + '>' + field + '</option>');
      data.push({id: field, text: field});
    });
    $select.html(sel);
    return $('#id_name').djangoAdminSelect2({
      ajax: {
        data: function (request_data) {
          data = data.filter(function(item) {
            if (request_data.term) {return item.text.startsWith(request_data.term)}
            return true;
          });
        },
        processResults: function (get_data, page) {
          return {results: data};
        }
      }
    });
  };
  $(document).ready(function () {
    $('#id_content_type').change();
    $('#id_content_type').change(function () {
      $('#id_name').removeAttr('readonly');
      if (! $(this).val()) {
        $('#id_name').attr('readonly', true);
        return;
      }
      var esc = encodeURIComponent;
      $.get({
        url: '?id_ct=' + $(this).val(),
        success: function (data, textStatus, jqXHR) {
          if (data.errors) {
            return alert(data.errors)
          }
          generic_view_json(data.fields, data.text);
        },
        dataType: "json"
      });
    });
  });
}(jQuery));
