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
              return gadget.jio_getAttachment(doc.relative_url,
                url + doc.relative_url + "/SoftwareRelease_requestSoftwareInstallation?computer=" + doc.computer);
            });
        })
        .push(function (key) {
          return gadget.notifySubmitted({message: 'New Software Installation created.', status: 'success'})
            .push(function () {
              // Workaround, find a way to open document without break gadget.
              return gadget.redirect({"command": "change",
                                    "options": {"jio_key": key, "page": "slap_controller"}});
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
            gadget.jio_get(options.jio_key),
            gadget.jio_get(options.computer_jio_key)
          ]);
        })
        .push(function (result) {
          var doc = result[1],
              computer = result[2];
          return result[0].render({
            erp5_document: {
              "_embedded": {"_view": {
                "my_url_string": {
                  "description": "The name of a document in ERP5",
                  "title": "Software Release to be Installed",
                  "default": doc.url_string,
                  "css_class": "",
                  "required": 0,
                  "editable": 0,
                  "key": "title",
                  "hidden": 0,
                  "type": "StringField"
                },
                "your_computer_title": {
                  "description": "The name of a document in ERP5",
                  "title": "Target Computer Title",
                  "default": computer.title,
                  "css_class": "",
                  "required": 0,
                  "editable": 0,
                  "key": "title",
                  "hidden": 0,
                  "type": "StringField"
                },
                "your_computer_reference": {
                  "description": "The name of a document in ERP5",
                  "title": "Target Computer Reference",
                  "default": computer.reference,
                  "css_class": "",
                  "required": 0,
                  "editable": 0,
                  "key": "computer_reference",
                  "hidden": 0,
                  "type": "StringField"
                },
                "your_computer": {
                  "description": "Computer",
                  "title": "Computer",
                  "default": options.computer_jio_key,
                  "css_class": "",
                  "required": 1,
                  "editable": 1,
                  "key": "computer",
                  "hidden": 1,
                  "type": "StringField"
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
                [["my_url_string"], ["your_computer_title"], ["your_computer_reference"],
                 ["your_computer"], ["my_relative_url"]]
              ]]
            }
          })
          .push(function () {
            return gadget.updateHeader({
              page_title: "Proceed to Supply Software  " + doc.title + " on " +  computer.reference,
              submit_action: true
            });
          });
        });
    });
}(window, rJS, RSVP));