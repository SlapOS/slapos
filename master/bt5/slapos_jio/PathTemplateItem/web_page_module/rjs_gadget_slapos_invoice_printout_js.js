/*globals console, window, rJS, RSVP, loopEventListener, i18n, $*/
/*jslint indent: 2, nomen: true, maxlen: 80*/

(function (window, rJS, RSVP) {
  "use strict";
  var gadget_klass = rJS(window);

  gadget_klass
    .declareAcquiredMethod("jio_get", "jio_get")
    .declareAcquiredMethod("getSetting", "getSetting")
    .declareAcquiredMethod("translateHtml", "translateHtml")

    .declareMethod("getContent", function () {
      return {};
    })
    .declareMethod("render", function (options) {
      var gadget = this;
      return gadget.getElement()
        .push(function (element) {
          return gadget.getSetting("hateoas_url")
            .push(function (hateoas_url) {
              var link = "<a href=" + hateoas_url + "/" + options.value.jio_key + "/SaleInvoiceTransaction_viewSlapOSPrintout> <img src='pdf_icon.png'></img> </a>";
              element.innerHTML = link;
              return element;
            });
        });
    });
}(window, rJS, RSVP));