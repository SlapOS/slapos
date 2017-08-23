/*global window, rJS, RSVP */
/*jslint nomen: true, indent: 2, maxerr: 3 */
(function (window, rJS, RSVP) {
  "use strict";

  rJS(window)
    /////////////////////////////////////////////////////////////////
    // Acquired methods
    /////////////////////////////////////////////////////////////////
    .declareAcquiredMethod("updateHeader", "updateHeader")
    .declareAcquiredMethod("jio_getAttachment", "jio_getAttachment")
    .declareAcquiredMethod("getSetting", "getSetting")
    .declareAcquiredMethod("getUrlFor", "getUrlFor")
    .declareAcquiredMethod("redirect", "redirect")
    .declareAcquiredMethod("jio_post", "jio_post")
    .declareAcquiredMethod("jio_get", "jio_get")
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
        .push(function (content) {
          var property, doc = {};
          for (property in content) {
            if ((content.hasOwnProperty(property)) &&
                // Remove undefined keys added by Gadget fields
                (property !== "undefined") &&
                // Remove default_*:int keys added by ListField
                !(property.endsWith(":int") && property.startsWith("default_"))) {
              doc[property] = content[property];
            }

          }
          return gadget.jio_post(doc);
        })
        .push(function (key) {
          return gadget.notifySubmitted({message: 'New Ticket created.', status: 'success'})
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
      gadget.state.jio_key = options.jio_key;

      return RSVP.Queue()
        .push(function () {
          return gadget.getSetting("hateoas_url");
        })
        .push(function (hateoas_url) {
          return RSVP.all([
            gadget.getDeclaredGadget('form_view'),
            gadget.jio_getAttachment("ticket_resource_list",
               hateoas_url + "Ticket_getResourceItemListAsJSON"),
            gadget.getSetting("me")
          ]);
        })
        .push(function (result) {
          return result[0].render({
            erp5_document: {
              "_embedded": {"_view": {
                "my_title": {
                  "description": "The name of a document in ERP5",
                  "title": "Subject",
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
                  "title": "Message",
                  "default": "",
                  "css_class": "",
                  "required": 1,
                  "editable": 1,
                  "key": "description",
                  "hidden": 0,
                  "type": "TextAreaField"
                },
                "my_resource": {
                  "description": "The name of a document in ERP5",
                  "title": "Ticket Type",
                  "default": "",
                  "items": result[1],
                  "css_class": "",
                  "required": 1,
                  "editable": 1,
                  "key": "resource",
                  "hidden": 0,
                  "type": "ListField"
                },
                "my_destination_decision": {
                  "description": "The name of a document in ERP5",
                  "title": "Current User",
                  "default": result[2],
                  "css_class": "",
                  "required": 1,
                  "editable": 1,
                  "key": "destination_decision",
                  "hidden": 1,
                  "type": "StringField"
                },
                "my_specialise": {
                  "description": "",
                  "title": "Trade Condition",
                  // Auto Set a hardcoded trade Condition
                  // Please replace it by a getSetting.
                  "default": "sale_trade_condition_module/slapos_ticket_trade_condition",
                  "css_class": "",
                  "required": 1,
                  "editable": 1,
                  "key": "specialise",
                  "hidden": 1,
                  "type": "StringField"
                },
                "my_aggregate": {
                  "description": "",
                  "title": "Aggregate",
                  "default": gadget.state.jio_key,
                  "css_class": "",
                  "required": 1,
                  "editable": 1,
                  "key": "aggregate",
                  "hidden": 1,
                  "type": "StringField"
                },
                "my_portal_type": {
                  "description": "The name of a document in ERP5",
                  "title": "Portal Type",
                  "default": "Support Request",
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
                  "default": "support_request_module",
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
                [["my_resource"]]
              ], [
                "center",
                [["my_title"], ["my_description"], ["my_specialise"], ["my_destination_decision"], ["my_aggregate"], ["my_portal_type"], ["my_parent_relative_url"]]
              ]]
            }
          })
          .push(function () {
            return gadget.jio_get(gadget.state.jio_key)
              .push(function (doc) {
                gadget.updateHeader({
                  page_title: "New Ticket related to " + doc.title,
                  submit_action: true
                });
              });
          });
        });
    });
}(window, rJS, RSVP));