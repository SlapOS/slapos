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
          return gadget.jio_post(doc);
        })
        .push(function (key) {
          return gadget.notifySubmitted({message: 'New Project created.', status: 'success'})
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

    .declareMethod("render", function () {
      var gadget = this;
      return RSVP.Queue()
        .push(function () {
          return RSVP.all([
            gadget.getDeclaredGadget('form_view'),
            gadget.getSetting('me')
          ]);
        })
        .push(function (result) {
          return result[0].render({
            erp5_document: {
              "_embedded": {"_view": {
                "my_title": {
                  "description": "The name of a document in ERP5",
                  "title": "Title",
                  "default": "",
                  "css_class": "",
                  "required": 1,
                  "editable": 1,
                  "key": "title",
                  "hidden": 0,
                  "type": "StringField"
                },
                "my_description": {
                  "description": "The name of a document in ERP5",
                  "title": "Description",
                  "default": "",
                  "css_class": "",
                  "required": 0,
                  "editable": 1,
                  "key": "description",
                  "hidden": 0,
                  "type": "TextAreaField"
                },
                "my_destination_decision": {
                  "description": "",
                  "title": "Destination Decision",
                  "default": result[1],
                  "css_class": "",
                  "required": 1,
                  "editable": 1,
                  "key": "destination_decision",
                  "hidden": 1,
                  "type": "StringField"
                },
                "my_portal_type": {
                  "description": "The name of a document in ERP5",
                  "title": "Portal Type",
                  "default": "Project",
                  "css_class": "",
                  "required": 1,
                  "editable": 1,
                  "key": "portal_type",
                  "hidden": 1,
                  "type": "StringField"
                },
                "my_parent_relative_url": {
                  "description": "",
                  "title": "Parent Relative Url",
                  "default": "project_module",
                  "css_class": "",
                  "required": 1,
                  "editable": 1,
                  "key": "parent_relative_url",
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
                "left",
                [["my_title"], ["my_description"], ["my_destination_decision"], ["my_portal_type"], ["my_parent_relative_url"]]
              ]]
            }
          });
        })
        .push(function () {
          return gadget.updateHeader({
            page_title: "New Project",
            submit_action: true
          });
        });
    });
}(window, rJS, RSVP));