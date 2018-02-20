/*globals console, window, document, rJS, RSVP, loopEventListener, i18n, Handlebars $*/
/*jslint indent: 2, nomen: true, maxlen: 80*/

(function (window, document, rJS, RSVP, Handlebars) {
  "use strict";
  var gadget_klass = rJS(window);

  gadget_klass
    .declareAcquiredMethod("jio_get", "jio_get")
    .declareAcquiredMethod("getSetting", "getSetting")
    .declareAcquiredMethod("jio_getAttachment", "jio_getAttachment")
    .declareAcquiredMethod("translateHtml", "translateHtml")

    .declareMethod("getContent", function () {
      return {};
    })
    .declareMethod("render", function (options) {
      var gadget = this, a, value;
      return gadget.getElement()
        .push(function (element) {
          value = options.value;
          if (options.value &&
              (options.value.startsWith("http://") ||
                 options.value.startsWith("https://"))) {
            a = document.createElement('a');
            a.setAttribute("href", options.value);
            a.setAttribute("target", "_blank");
            a.innerText = options.value;
            value = a.outerHTML;
          }
          element.innerHTML = value;
          return element;
        });
    });
}(window, document, rJS, RSVP, Handlebars));