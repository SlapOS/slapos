/*global document, window, Option, rJS, RSVP, Chart*/
/*jslint nomen: true, indent: 2, maxerr: 3 */
(function (window, rJS, RSVP) {
  "use strict";

  rJS(window)
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

    .allowPublicAcquisition("updateHeader", function () {
      return;
    })

    /////////////////////////////////////////////////////////////////
    // declared methods
    /////////////////////////////////////////////////////////////////
    .declareMethod('getContent', function () {
      return;
    })
    .declareMethod("render", function (options) {
      var gadget = this,
          result = options.value;
      return gadget.getElement().push(function (element) {
        return gadget.declareGadget("gadget_erp5_page_map.html", {
          scope: "map",
          element: element.querySelector(".map-gadget")
        });
      })
      .push(function (map_gadget) {
        return map_gadget.render({
          zoom : 40,
          marker_list : result
        });
      });
    });
}(window, rJS, RSVP));