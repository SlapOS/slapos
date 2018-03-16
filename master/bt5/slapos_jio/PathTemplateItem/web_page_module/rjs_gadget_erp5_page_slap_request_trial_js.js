/*global window, rJS, RSVP, btoa */
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
              return gadget.jio_getAttachment(doc.relative_url,
                url + doc.relative_url +
                  "/TrialCondition_requestFreeTrial?default_email_text=" + encodeURIComponent(doc.default_email_text) +
                  "&default_input0=" + encodeURIComponent(doc.default_input0) +
                  "&default_input1=" + encodeURIComponent(doc.default_input1));
            });
        })
        .push(function (result) {
          return gadget.redirect({"command": "change",
                                  "options": {"jio_key": "/",
                                              "page": "slap_trial_request_message",
                                              "result": result}});
        });
    })

    .declareMethod("triggerSubmit", function () {
      return this.element.querySelector('button[type="submit"]').click();
    })

    .declareMethod("render", function (options) {
      var gadget = this;
      return RSVP.Queue()
        .push(function () {
          return gadget.getSetting("hateoas_url");
        })
        .push(function (hateoas_url) {
          return RSVP.all([
            gadget.getDeclaredGadget('form_view'),
            gadget.jio_getAttachment("/",
              hateoas_url + "/ERP5Site_getTrialConfigurationAsJSON")
          ]);
        })
        .push(function (result) {
          var i, doc;
          for (i in result[1]) {
            if (result[1][i].url === options.jio_key) {
              doc = result[1][i];
              break;
            }
          }
          return result[0].render({
            erp5_document: {
              "_embedded": {"_view": {
                "your_product_description": {
                  "description": "The name of a document in ERP5",
                  "title": "",
                  "default": doc.product_description,
                  "css_class": "",
                  "required": 0,
                  "editable": 0,
                  "key": "product_description",
                  "hidden": 0,
                  "type": "EditorField"
                },
                "your_email": {
                  "description": "The name of a document in ERP5",
                  "title": "Your Email",
                  "default": "",
                  "css_class": "",
                  "required": 1,
                  "editable": 1,
                  "key": "default_email_text",
                  "hidden": 0,
                  "type": "EmailField"
                },
                "your_input0": {
                  "description": "The name of a document in ERP5",
                  "title": doc.input_list.length > 0 ? doc.input_list[0] : "",
                  "default": "",
                  "css_class": "",
                  "required": 0,
                  "editable": 1,
                  "key": "default_input0",
                  "hidden": doc.input_list.length > 0 ? 0 : 1,
                  "type": "StringField"
                },
                "your_input1": {
                  "description": "The name of a document in ERP5",
                  "title": doc.input_list.length > 1 ? doc.input_list[1] : "",
                  "default": "",
                  "css_class": "",
                  "required": 0,
                  "editable": 1,
                  "key": "default_input1",
                  "hidden": doc.input_list.length > 1 ? 0 : 1,
                  "type": "StringField"
                },
                "your_terms_of_service": {
                  "default": doc.terms_of_service,
                  "title": "Terms of Service",
                  "css_class": "",
                  "required": 0,
                  "editable": 0,
                  "key": "terms_of_service",
                  "hidden": 0,
                  "type": "EditorField",
                  //"url": "gadget_editor.html",
                  "sandbox": "iframe"
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
                [["your_product_description"], ["your_email"],
                 ["your_input0"], ["your_input1"],
                 ["your_terms_of_service"], ["my_relative_url"]]
              ]]
            }
          })
          .push(function () {
            return gadget.updateHeader({
              page_title: "Request a Trial for " + doc.name,
              submit_action: true
            });
          });
        });
    });
}(window, rJS, RSVP));