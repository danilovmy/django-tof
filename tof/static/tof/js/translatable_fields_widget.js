(function ($) {
  "use strict";
  function dismissRelatedLookupPopupLang(win, chosenId) {
    var elem = document.getElementById(win.name);
    win.close();
    if (elem.className.includes("ltab")) {

      if (!document.getElementById(chosenId + '_' + elem.dataset['idTemplate'])) {
        var newItab = $(".itab", $(elem.parentNode)).first().clone();
        newItab.attr("id", chosenId + '_' + elem.dataset['idTemplate']);
        newItab.insertBefore($(elem));

        var newLtab = $(".ltab", $(elem.parentNode)).first().clone();
        newLtab.attr("for", chosenId + '_' + elem.dataset['idTemplate']).text(chosenId);
        newLtab.insertBefore($(elem));

        var newTab = $(".tab", $(elem.parentNode)).first().clone();
        newTab.children().attr({id: elem.dataset['idTemplate'] + '_' + chosenId , name: elem.dataset['nameTemplate'] + '_' + chosenId}).text("").val("");
        newTab.insertBefore($(elem));
        // especcially for ckeditor
        if (newTab.children()[0].dataset['fieldId']) {
          var newInput = document.getElementById(newTab.children()[0].dataset['fieldId']).cloneNode(false);
          newInput.id = elem.dataset['idTemplate'] + '_' + chosenId;
          newInput.dataset['id'] = newInput.id;
          newInput.name = elem.dataset['nameTemplate'] + '_' + chosenId;
          newTab.children()[0].dataset['fieldId'] = newInput.id;
          newTab.children().removeAttr('id').removeAttr('name')[0].appendChild(newInput);
          CKEDITOR.replace(newInput, JSON.parse(newInput.dataset['config'])).setData('');
        }
      }
      $('.ltab[for="' + chosenId + '_' + elem.dataset['idTemplate'] + '"]').click();
    }

  }
  $(document).ready(function () {
    window.dismissRelatedLookupPopup = dismissRelatedLookupPopupLang;
  });
})(typeof django === 'object' && django.jQuery || jQuery);
