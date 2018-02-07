/*global window, rJS, RSVP */
/*jslint nomen: true, indent: 2, maxerr: 3 */
(function (window, rJS, RSVP) {
  "use strict";

  rJS(window)
    /////////////////////////////////////////////////////////////////
    // Acquired methods
    /////////////////////////////////////////////////////////////////
    .declareAcquiredMethod("updateHeader", "updateHeader")
    .declareAcquiredMethod("getSetting", "getSetting")
    .declareAcquiredMethod("getUrlFor", "getUrlFor")
    .declareAcquiredMethod("redirect", "redirect")
    .declareAcquiredMethod("jio_post", "jio_post")
    .declareAcquiredMethod("jio_get", "jio_get")
    .declareAcquiredMethod("jio_putAttachment", "jio_putAttachment")
    .declareAcquiredMethod("jio_getAttachment", "jio_getAttachment")

    .declareAcquiredMethod("notifySubmitting", "notifySubmitting")
    .declareAcquiredMethod("notifySubmitted", 'notifySubmitted')



    /////////////////////////////////////////////////////////////////
    // declared methods
    /////////////////////////////////////////////////////////////////
    .allowPublicAcquisition('notifySubmit', function () {
      return this.triggerSubmit();
    })

    .onEvent('submit', function () {
      var gadget = this;
      return gadget.notifySubmitting()
        .push(function () {
          return gadget.getDeclaredGadget('form_view');
        })
        .push(function (form_gadget) {
          return form_gadget.getContent();
        })
        .push(function (doc) {
          return gadget.getSetting("hateoas_url")
            .push(function (url) {
              return gadget.jio_putAttachment(doc.relative_url,
                url + doc.relative_url + "/SoftwareRelease_requestHostingSubscription", doc);
            });
        })
        .push(function (key) {
          return gadget.notifySubmitted({message: 'New service created.', status: 'success'})
            .push(function () {
              // Workaround, find a way to open document without break gadget.
              return gadget.redirect({"command": "change",
                                    "options": {"jio_key": "/", "page": "slap_service_list"}});
            });
        });
    })

    .declareMethod("triggerSubmit", function () {
      return this.element.querySelector('button[type="submit"]').click();
    })

    .declareMethod("render", function (options) {
      var gadget = this;
      if (options.intent !== "request") {
        throw new Error("Intent not supported");
      }
      return RSVP.Queue()
        .push(function () {
          return gadget.updateHeader({
            page_title: "Requesting a service..."
          });
        })
        .push(function () {
          return gadget.getSetting("hateoas_url")
            .push(function (url) {
              return gadget.jio_getAttachment("/",
                url + "/SoftwareProduct_getSoftwareReleaseAsHateoas?software_release=" + options.software_release
                   );
            });
        })
        .push(function (jio_key) {
          if (options.auto === undefined) {
            return gadget.redirect({"command": "change",
              "options": {"jio_key": jio_key, "page": "slap_add_hosting_subscription",
                          "title": options.title}});
          }
          // The auto is set, so we move foward to auto request the SR
          options.jio_key = jio_key;
          return RSVP.all([
            gadget.getDeclaredGadget('form_view'),
            gadget.jio_get(jio_key),
            gadget.getSetting("hateoas_url")
          ]);
        })
        .push(function (result) {
          var software_release = result[1],
              url = result[2],
              title = options.software_title ? options.software_title: "Instance ",
              doc = {};

          doc.url_string = software_release.url_string;
          doc.title = title;
          doc.text_content = "";
          doc.relative_url = options.jio_key;
          return gadget.notifySubmitting()
            .push(function () {
              return gadget.jio_putAttachment(doc.relative_url,
                    url + doc.relative_url + "/SoftwareRelease_requestHostingSubscription", doc);
            })
            .push(function (key) {
              return gadget.notifySubmitted({message: 'New service created.', status: 'success'})
                .push(function () {
                  // Workaround, find a way to open document without break gadget.
                  return gadget.redirect({"command": "change",
                                  "options": {"jio_key": "/", "page": "slap_service_list"}});
                });
            });
        });
    });
}(window, rJS, RSVP));