/*globals console, window, rJS, RSVP, loopEventListener, i18n, Handlebars $*/
/*jslint indent: 2, nomen: true, maxlen: 80*/

(function (window, rJS, RSVP, Handlebars) {
  "use strict";
  var gadget_klass = rJS(window),
    download_invoice_source = gadget_klass.__template_element
                         .getElementById("download-link-template")
                         .innerHTML,
    download_invoice_template = Handlebars.compile(download_invoice_source);

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
              var link = hateoas_url + "/" +
                         options.value.jio_key +
                         "/SaleInvoiceTransaction_viewSlapOSPrintout";
              element.innerHTML = download_invoice_template({
                invoice_url: link
              });
              return element;
            });
        });
    });
}(window, rJS, RSVP, Handlebars));