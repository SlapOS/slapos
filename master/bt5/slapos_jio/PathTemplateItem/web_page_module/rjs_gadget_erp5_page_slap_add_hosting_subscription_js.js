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
      return RSVP.Queue()
        .push(function () {
          return RSVP.all([
            gadget.getDeclaredGadget('form_view'),
            gadget.jio_get(options.jio_key)
          ]);
        })
        .push(function (result) {
          var doc = result[1];
          return result[0].render({
            erp5_document: {
              "_embedded": {"_view": {
                "my_url_string": {
                  "description": "The name of a document in ERP5",
                  "title": "Software Release URL",
                  "default": doc.url_string,
                  "css_class": "",
                  "required": 0,
                  "editable": 0,
                  "key": "title",
                  "hidden": 0,
                  "type": "StringField"
                },
                "your_title": {
                  "description": "The name of a document in ERP5",
                  "title": "Title",
                  "default": "",
                  "css_class": "",
                  "required": 0,
                  "editable": 1,
                  "key": "title",
                  "hidden": 0,
                  "type": "StringField"
                },
                "your_text_content": {
                  "description": "The name of a document in ERP5",
                  "title": "Instance Parameter",
                  "default": "",
                  "css_class": "",
                  "required": 1,
                  "editable": 1,
                  "key": "text_content",
                  "hidden": 0,
                  "type": "TextAreaField"
                },
                "your_computer_guid": {
                  "description": "The name of a document in ERP5",
                  "title": "Computer",
                  "default": "",
                  "items": doc.computer_guid,
                  "css_class": "",
                  "required": 1,
                  "editable": 1,
                  "key": "computer_guid",
                  "hidden": 0,
                  "type": "ListField"
                },
                "my_relative_url": {
                  "description": "",
                  "title": "Parent Relative Url",
                  "default": options.jio_key,
                  "css_class": "",
                  "required": 1,
                  "editable": 1,
                  "key": "relative_url",
                  "hidden": 1,
                  "type": "StringField"
                }
              }},
              "_links": {
                "type": {
                  // form_list display portal_type in header
                  name: ""
                }
              }
            },
            form_definition: {
              group_list: [[
                "center",
                [["my_url_string"], ["your_title"], ["your_text_content"],
                 ["your_computer_guid"], ["my_portal_type"], ["my_relative_url"]]
              ]]
            }
          })
          .push(function () {
            return gadget.updateHeader({
              page_title: "Request Service: " + doc.title,
              submit_action: true
            });
          });
        });
    });
}(window, rJS, RSVP));