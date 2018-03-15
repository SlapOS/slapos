/*global document, window, Option, rJS, RSVP, Chart, UriTemplate, Handlebars*/
/*jslint nomen: true, indent: 2, maxerr: 3 */
(function (window, rJS, RSVP, Handlebars) {
  "use strict";
  var gadget_klass = rJS(window),
      offer_source = gadget_klass.__template_element
                         .getElementById("offer-template")
                         .innerHTML,
      offer_template = Handlebars.compile(offer_source);

  gadget_klass
    .ready(function (gadget) {
      gadget.property_dict = {};
      return gadget.getElement()
        .push(function (element) {
          gadget.property_dict.element = element;
          gadget.property_dict.deferred = RSVP.defer();
        });
    })
    /////////////////////////////////////////////////////////////////
    // Acquired methods
    /////////////////////////////////////////////////////////////////
    .declareAcquiredMethod("jio_getAttachment", "jio_getAttachment")
    .declareAcquiredMethod("translateHtml", "translateHtml")
    .declareAcquiredMethod("redirect", "redirect")
    .declareAcquiredMethod("updateHeader", "updateHeader")
    .declareAcquiredMethod("updateConfiguration", "updateConfiguration")
    .declareAcquiredMethod("getSetting", "getSetting")
    .declareAcquiredMethod("getUrlFor", "getUrlFor")
    .declareAcquiredMethod("jio_allDocs", "jio_allDocs")
    .declareAcquiredMethod("jio_getAttachment", "jio_getAttachment")

    /////////////////////////////////////////////////////////////////
    // declared methods
    /////////////////////////////////////////////////////////////////
    .declareMethod("render", function () {
      var gadget = this, offer_list = [];
      return new RSVP.Queue()
        .push(function () {
          return gadget.getSetting("hateoas_url");
        })
        .push(function (hateoas_url) {
          return gadget.jio_getAttachment("/",
            hateoas_url + "/ERP5Site_getTrialConfigurationAsJSON");
        })
        .push(function (queue_list) {
          var i, url_queue = [];
          gadget.queue_list = queue_list;
          for (i in gadget.queue_list) {
            if (gadget.queue_list.hasOwnProperty(i)) {
              url_queue.push(
               gadget.getUrlFor({command: 'change', options: {jio_key: gadget.queue_list[i].url, page: "slap_request_trial"}})
              );
            }
          }
          return RSVP.all(url_queue);
        })
       .push(function (url_list) {
          var i;
          for (i in gadget.queue_list) {
            if (gadget.queue_list.hasOwnProperty(i)) {
              offer_list.push(offer_template({
                  url: url_list[i],
                  header: gadget.queue_list[i].header,
                  name: gadget.queue_list[i].name,
                  footer: gadget.queue_list[i].footer,
                  price: gadget.queue_list[i].price
                }));
            }
          }
          return gadget.getElement()
            .push(function (element) {
              var ul = element.querySelector("ul");
              ul.innerHTML = offer_list.join(" ");
              return element;
            });
        })
        .push(function () {
          return gadget.updateHeader({
            page_title: "Welcome to Free Trial Program"
          });
        });
    });
}(window, rJS, RSVP, Handlebars));