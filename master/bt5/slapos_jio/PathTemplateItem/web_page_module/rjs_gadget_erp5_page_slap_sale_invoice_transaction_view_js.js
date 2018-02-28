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
    .declareAcquiredMethod("updateDocument", "updateDocument")
    .declareAcquiredMethod("jio_getAttachment", "jio_getAttachment")
    .declareAcquiredMethod("jio_putAttachment", "jio_putAttachment")
    .declareAcquiredMethod("notifySubmitting", "notifySubmitting")
    .declareAcquiredMethod("notifySubmitted", 'notifySubmitted')
    .declareAcquiredMethod("jio_allDocs", "jio_allDocs")

    /////////////////////////////////////////////////////////////////
    // declared methods
    /////////////////////////////////////////////////////////////////

    .declareMethod("render", function (options) {
      return this.changeState({
        jio_key: options.jio_key,
        doc: options.doc,
        editable: 1
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
          return gadget.updateDocument(content);
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
          var start_date = new Date(gadget.state.doc.start_date),
              total_price = window.parseFloat(gadget.state.doc.total_price).toFixed(2);
          return form_gadget.render({
            erp5_document: {
              "_embedded": {"_view": {
                "my_start_date": {
                  "allow_empty_time": 0,
                  "ampm_time_style": 0,
                  "css_class": "date_field",
                  "date_only": 1,
                  "description": "The Date",
                  "editable": 0,
                  "hidden": 0,
                  "hidden_day_is_last_day": 0,
                  "default": start_date.toUTCString(),
                  "key": "date",
                  "required": 0,
                  "timezone_style": 0,
                  "title": "Date",
                  "type": "DateTimeField"
                },
                "my_reference": {
                  "description": "",
                  "title": "Reference",
                  "default": gadget.state.doc.reference,
                  "css_class": "",
                  "required": 1,
                  "editable": 0,
                  "key": "reference",
                  "hidden": 0,
                  "type": "StringField"
                },
                "my_total_price": {
                  "description": "",
                  "title": "Total",
                  "default": total_price,
                  "css_class": "",
                  "required": 1,
                  "editable": 0,
                  "key": "total_price",
                  "hidden": 0,
                  "type": "StringField"
                },
                "my_resource_title": {
                  "description": "",
                  "title": "Currency",
                  "default": gadget.state.doc.resource_title,
                  "css_class": "",
                  "required": 1,
                  "editable": 0,
                  "key": "resource_title",
                  "hidden": 0,
                  "type": "StringField"
                },
                "my_payment_state": {
                  "description": "",
                  "title": "Payment State",
                  "default": {jio_key: gadget.state.jio_key},
                  "css_class": "",
                  "required": 1,
                  "editable": 0,
                  "url": "gadget_slapos_invoice_state.html",
                  "sandbox": "",
                  "key": "payment_state",
                  "hidden": 0,
                  "type": "GadgetField"
                },
                "my_download": {
                  "description": "",
                  "title": "Download",
                  "default": {jio_key: gadget.state.jio_key},
                  "css_class": "",
                  "required": 1,
                  "editable": 0,
                  "url": "gadget_slapos_invoice_printout.html",
                  "sandbox": "",
                  "key": "monitoring_status",
                  "hidden": 0,
                  "type": "GadgetField"
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
                [["my_start_date"], ["my_reference"], ["my_total_price"],
                 ["my_resource_title"], ['my_payment_state'], ["my_download"]]
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
        .push(function (url_list) {
          var start_date = new Date(gadget.state.doc.start_date),
            header_dict = {
              selection_url: url_list[1],
              page_title: "Invoice : " + start_date.toUTCString()
            };
          if (!gadget.state.editable) {
            header_dict.edit_content = url_list[0];
          }
          return gadget.updateHeader(header_dict);
        });
    });
}(window, rJS, RSVP, jIO, Blob));