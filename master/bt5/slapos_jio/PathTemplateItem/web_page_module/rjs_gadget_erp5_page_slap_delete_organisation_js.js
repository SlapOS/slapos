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
                url + doc.relative_url + "/Organisation_closeRelatedAssignment", {});
            });
        })
        .push(function () {
          return gadget.notifySubmitted({message: 'Site is Deleted.', status: 'success'})
            .push(function () {
              // Workaround, find a way to open document without break gadget.
              return gadget.redirect({"command": "change",
                                    "options": {jio_key: "/", "page": "slap_site_list"}});
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
          return gadget.getSetting("hateoas_url")
            .push(function (url) {
              return RSVP.all([
                gadget.getDeclaredGadget('form_view'),
                gadget.jio_get(options.jio_key),
                gadget.jio_getAttachment(options.jio_key,
                  url + options.jio_key + "/Organisation_hasItem")
              ]);
            });
        })
        .push(function (result) {
          options.doc = result[1];
          options.can_delete = result[2] ? 0: 1;
          return result[0].render({
            erp5_document: {
              "_embedded": {"_view": {
                "my_title": {
                  "description": "",
                  "title": "Organisation to be removed: ",
                  "default": options.doc.title,
                  "css_class": "",
                  "required": 1,
                  "editable": 0,
                  "key": "title_label",
                  "hidden": 0,
                  "type": "StringField"
                },
                "message": {
                  "description": "",
                  "title": "Warning",
                  "default": "You cannot delete this object because you have associated Computers and/or services.",
                  "css_class": "",
                  "required": 1,
                  "editable": 0,
                  "key": "title_label",
                  "hidden": options.can_delete,
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
                "left",
                [["my_title"], ["my_relative_url"]]
              ], [
                "bottom",
                [["message"]]
              ]]
            }
          });
        })
        .push(function () {
          return RSVP.all([
            gadget.getUrlFor({command: "change", options: {editable: true}}),
            gadget.getUrlFor({command: 'history_previous'})
          ]);
        })
        .push(function (result) {
          var header_dict = {
            selection_url: result[1],
            page_title: "Delete Site: " + options.doc.title
          };
          if (options.can_delete) {
            header_dict.submit_action = true;
          }
          return gadget.updateHeader(header_dict);
        });
    });
}(window, rJS, RSVP));