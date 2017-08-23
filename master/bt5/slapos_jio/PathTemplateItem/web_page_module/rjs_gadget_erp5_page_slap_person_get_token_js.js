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
                url + doc.relative_url + "/Base_getCredentialToken");
            })
            .push(function (result) {
              var msg;
              if (result) {
                msg = 'Token is Requested.';
              } else {
                msg = 'This person already has one certificate, please revoke it before request a new one..';
                result = {};
              }
              return gadget.notifySubmitted({message: msg, status: 'success'})
                .push(function () {
                  // Workaround, find a way to open document without break gadget.
                  result.jio_key = doc.relative_url;
                  return gadget.render(result);
                });
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
            gadget.getDeclaredGadget('form_view')
          ]);
        })
        .push(function (result) {
          return result[0].render({
            erp5_document: {
              "_embedded": {"_view": {
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
                },
                "my_access_token": {
                  "description": "",
                  "title": "Your Token",
                  "default": options.access_token,
                  "css_class": "",
                  "required": 1,
                  "editable": 0,
                  "key": "certificate",
                  "hidden": (options.access_token === undefined) ? 1: 0,
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
                [["my_access_token"], ["my_relative_url"]]
              ]]
            }
          });
        })
        .push(function () {
          var header_dict = {
            page_title: "Request New Token",
            submit_action: true
          };
          return gadget.updateHeader(header_dict);
        });
    });
}(window, rJS, RSVP));