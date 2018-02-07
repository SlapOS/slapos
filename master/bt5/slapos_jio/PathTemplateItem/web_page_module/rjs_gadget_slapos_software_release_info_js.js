/*globals console, window, rJS, RSVP, loopEventListener, i18n, Handlebars $*/
/*jslint indent: 2, nomen: true, maxlen: 80*/

(function (window, rJS, RSVP, Handlebars) {
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
      var gadget = this;
      return new RSVP.Queue()
        .push(function () {
          return RSVP.all([
            gadget.getElement(),
            gadget.getSetting("hateoas_url")
          ]);
        })
        .push(function (result) {
          var hateoas_url = result[1],
              element = result[0];

          return gadget.jio_getAttachment(options.value.jio_key,
                hateoas_url +  options.value.jio_key +
                "/SoftwareInstallation_getSoftwareReleaseInformation")
            .push(function (info) {
              console.log(info);

              element.innerHTML = info;
              return info;
            });
        });
    });
}(window, rJS, RSVP, Handlebars));