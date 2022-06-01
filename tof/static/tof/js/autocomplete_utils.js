'use strict'

function concrete_search(obj) {
    if (obj.form.elements[obj.dataset.name]) {
        set_search(obj.form.elements[obj.dataset.name], obj)
    };
}

function set_search(item, obj) {
    item.dataset.limitChoicesTo = JSON.stringify({...JSON.parse(item.dataset.limitChoicesTo || '""'), ...JSON.parse('{"' + obj.name + '":"' + obj.value + '"}')})
    patch_url(item)
}

function patch_url(item) {
    django.jQuery.each(Object.keys(item), function(idx, key) {
        if (item[key].select2) {
            patch_ajaxData(item, item[key].select2.dataAdapter.ajaxOptions, item[key].select2.dataAdapter.ajaxOptions.data)
            return false
        }
    })
}

function patch_ajaxData(item, ajaxOptions, baseData) {
   ajaxOptions.data = function (params) {
       return { ...baseData(params), ...JSON.parse(item.dataset.limitChoicesTo)}
   }
}
