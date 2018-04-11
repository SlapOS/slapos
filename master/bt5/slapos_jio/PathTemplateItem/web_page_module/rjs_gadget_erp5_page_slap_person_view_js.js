/*global window, rJS, RSVP, jIO, Blob */
/*jslint nomen: true, indent: 2, maxerr: 3 */
(function (window, rJS, RSVP, jIO, Blob) {
  "use strict";

  rJS(window)
    /////////////////////////////////////////////////////////////////
    // Acquired methods
    /////////////////////////////////////////////////////////////////
    .declareAcquiredMethod("updateHeader", "updateHeader")
    .declareAcquiredMethod("getUrlParameter", "getUrlParameter")
    .declareAcquiredMethod("getUrlFor", "getUrlFor")
    .declareAcquiredMethod("jio_get", "jio_get")
    .declareAcquiredMethod("getSetting", "getSetting")
    .declareAcquiredMethod("updateDocument", "updateDocument")
    .declareAcquiredMethod("jio_getAttachment", "jio_getAttachment")
    .declareAcquiredMethod("jio_putAttachment", "jio_putAttachment")
    .declareAcquiredMethod("jio_put", "jio_put")
    .declareAcquiredMethod("notifySubmitting", "notifySubmitting")
    .declareAcquiredMethod("notifySubmitted", 'notifySubmitted')
    /////////////////////////////////////////////////////////////////
    // declared methods
    /////////////////////////////////////////////////////////////////


    .declareMethod('updateDocument', function (content) {
      var gadget = this, property, doc = {};
      for (property in content) {
        if ((content.hasOwnProperty(property)) &&
            // Remove undefined keys added by Gadget fields
            (property !== "undefined") &&
            // Remove listboxes UIs
            (property !== "listbox_uid:list") &&
            // Remove default_*:int keys added by ListField
            !(property.endsWith(":int") && property.startsWith("default_"))) {
          doc[property] = content[property];
        }
      }
      return gadget.jio_put(gadget.state.jio_key, doc);
    })

    .declareMethod("render", function (options) {
      var gadget = this,
        jio_key;

      return new RSVP.Queue()
        .push(function () {
          return gadget.getSetting("me");
        })
        .push(function (me) {
          jio_key = me;
          return gadget.jio_get(me);
        })
        .push(function (doc) {
          options.doc = doc;
          return gadget.changeState({
            jio_key: jio_key,
            doc: doc,
            editable: 1
          });
        });
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
          return gadget.updateDocument(content)
            .push(function () {
              return gadget.updateHeader({
                page_title: "Your Account : " + content.first_name + " " + content.last_name
              });
            });
        })
        .push(function () {
          return gadget.notifySubmitted({message: 'Data Updated', status: 'success'});
        });
    })

    .declareMethod("triggerSubmit", function () {
      return this.element.querySelector('button[type="submit"]').click();
    })

    .onStateChange(function () {
      var gadget = this, data;
      return new RSVP.Queue()
        .push(function () {
          return gadget.getDeclaredGadget('form_view');
        })
        .push(function (form_gadget) {
          var editable = gadget.state.editable;
          return form_gadget.render({
            erp5_document: {
              "_embedded": {"_view": {
                "my_first_name": {
                  "description": "",
                  "title": "First Name",
                  "default": gadget.state.doc.first_name,
                  "css_class": "",
                  "required": 1,
                  "editable": editable,
                  "key": "first_name",
                  "hidden": 0,
                  "type": "StringField"
                },
                "my_last_name": {
                  "description": "",
                  "title": "Last Name",
                  "default": gadget.state.doc.last_name,
                  "css_class": "",
                  "required": 1,
                  "editable": editable,
                  "key": "last_name",
                  "hidden": 0,
                  "type": "StringField"
                },
                "my_default_email_text": {
                  "description": "",
                  "title": "Email",
                  "default": gadget.state.doc.default_email_text,
                  "css_class": "",
                  "required": 1,
                  "editable": editable,
                  "key": "default_email_text",
                  "hidden": 0,
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
                [["my_first_name"], ["my_last_name"], ["my_default_email_text"]]
              ]]
            }
          });
        })
        .push(function () {
          return gadget.getSetting("me");
        })
        .push(function (me) {
          return RSVP.all([
            gadget.getUrlFor({command: "change", options: {editable: true}}),
            gadget.getUrlFor({command: "change", options: {jio_key: me, page: "slap_person_revoke_certificate"}}),
            gadget.getUrlFor({command: "change", options: {jio_key: me, page: "slap_person_request_certificate"}}),
            gadget.getUrlFor({command: "change", options: {jio_key: me, page: "slap_person_get_token"}}),
            gadget.getUrlFor({command: "change", options: {page: "slapos"}})
          ]);
        })
        .push(function (url_list) {
          var header_dict = {
            page_title: "Your Account : " + gadget.state.doc.first_name + " " + gadget.state.doc.last_name,
            save_action: true,
            request_certificate_url: url_list[2],
            revoke_certificate_url: url_list[1],
            token_url: url_list[3],
            selection_url: url_list[4]
          };
          if (!gadget.state.editable) {
            header_dict.edit_content = url_list[0];
          }
          return gadget.updateHeader(header_dict);
        });
    });
}(window, rJS, RSVP, jIO, Blob));