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


    /////////////////////////////////////////////////////////////////
    // declared methods
    /////////////////////////////////////////////////////////////////
    .allowPublicAcquisition('notifySubmit', function () {
      return this.triggerSubmit();
    })

    .onEvent('submit', function () {
      var gadget = this;
      return gadget.getDeclaredGadget('form_view')
        .push(function (form_gadget) {
          return form_gadget.getContent();
        })
        .push(function (doc) {
          return gadget.jio_post(doc);
        })
        .push(function () {
          return gadget.redirect({"command": "change",
                                  "options": {"jio_key": gadget.state.jio_key,
                                              "page": "slap_controller"}});
        });
    })

    .declareMethod("triggerSubmit", function () {
      return this.element.querySelector('button[type="submit"]').click();
    })

    .declareMethod("render", function (options) {
      var gadget = this;
      gadget.state.jio_key = options.jio_key;

      return RSVP.Queue()
        .push(function () {
          return RSVP.all([
            gadget.getDeclaredGadget('form_view'),
            gadget.getSetting('me'),
            gadget.jio_get(gadget.state.jio_key)
          ]);
        })
        .push(function (result) {
          return result[0].render({
            erp5_document: {
              "_embedded": {"_view": {
                "my_title": {
                  "description": "The name of a document in ERP5",
                  "title": "Title",
                  "default": "Re: " + result[2].title,
                  "css_class": "",
                  "required": 1,
                  "editable": 1,
                  "key": "title",
                  "hidden": 1,
                  "type": "StringField"
                },
                "my_resource": {
                  "description": "Resource",
                  "title": "Title",
                  "default": result[2].resource,
                  "css_class": "",
                  "required": 1,
                  "editable": 1,
                  "key": "resource",
                  "hidden": 1,
                  "type": "StringField"
                },
                "my_text_content": {
                  "description": "Include your message",
                  "title": "Your Message",
                  "default": "",
                  "css_class": "",
                  "required": 1,
                  "editable": 1,
                  "key": "text_content",
                  "hidden": 0,
                  "type": "TextAreaField"
                },
                "my_source": {
                  "description": "",
                  "title": "Source",
                  "default": result[1],
                  "css_class": "",
                  "required": 1,
                  "editable": 1,
                  "key": "source",
                  "hidden": 1,
                  "type": "StringField"
                },
                "my_content_type": {
                  "description": "",
                  "title": "Content Type",
                  "default": "plain/text",
                  "css_class": "",
                  "required": 1,
                  "editable": 1,
                  "key": "content_type",
                  "hidden": 1,
                  "type": "StringField"
                },
                "my_follow_up": {
                  "description": "",
                  "title": "Follow up",
                  "default": gadget.state.jio_key,
                  "css_class": "",
                  "required": 1,
                  "editable": 1,
                  "key": "follow_up",
                  "hidden": 1,
                  "type": "StringField"
                },
                "my_portal_type": {
                  "description": "The name of a document in ERP5",
                  "title": "Portal Type",
                  "default": "Web Message",
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
                  "default": "event_module",
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
                "center",
                [["my_title"], ["my_text_content"], ["my_follow_up"],
                 ["my_portal_type"], ["my_parent_relative_url"],
                 ["my_follow_up"], ["my_source"]]
              ]]
            }
          });
        })
        .push(function () {
          return gadget.updateHeader({
            page_title: "New Ticket",
            submit_action: true
          });
        });
    });
}(window, rJS, RSVP));