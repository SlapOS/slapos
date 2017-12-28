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
                "my_software_release_title": {
                  "description": "",
                  "title": "Software Relase",
                  "default": gadget.state.doc.software_release_title,
                  "css_class": "",
                  "required": 1,
                  "editable": 0,
                  "key": "software_release_title",
                  "hidden": 0,
                  "type": "StringField"
                },
                "my_software_release_version": {
                  "description": "",
                  "title": "Software Relase Version",
                  "default": gadget.state.doc.software_release_version,
                  "css_class": "",
                  "required": 1,
                  "editable": 0,
                  "key": "software_release_version",
                  "hidden": 0,
                  "type": "StringField"
                },
                "my_aggregate_reference": {
                  "description": "",
                  "title": "Computer Reference",
                  "default": gadget.state.doc.aggregate_reference,
                  "css_class": "",
                  "required": 1,
                  "editable": 0,
                  "key": "aggregate_reference",
                  "hidden": 0,
                  "type": "StringField"
                },
                "my_aggregate_title": {
                  "description": "",
                  "title": "Computer",
                  "default": gadget.state.doc.aggregate_title,
                  "css_class": "",
                  "required": 1,
                  "editable": 0,
                  "key": "aggregate_title",
                  "hidden": 0,
                  "type": "StringField"
                },
                "my_reference": {
                  "description": "",
                  "title": "Reference",
                  "default": gadget.state.doc.reference,
                  "css_class": "",
                  "required": 1,
                  "editable": 0,
                  "key": "refeference",
                  "hidden": 0,
                  "type": "StringField"
                },
                "my_state": {
                  "description": "",
                  "title": "State",
                  "default": gadget.state.doc.state,
                  "css_class": "",
                  "required": 1,
                  "editable": 0,
                  "key": "State",
                  "hidden": 0,
                  "type": "StringField"
                },
                "my_usage": {
                  "description": "",
                  "title": "Usage",
                  "default": gadget.state.doc.usage,
                  "css_class": "",
                  "required": 1,
                  "editable": 0,
                  "key": "usage",
                  "hidden": 0,
                  "type": "StringField"
                },
                "my_url_string": {
                  "description": "",
                  "title": "Software Release URL",
                  "default": gadget.state.doc.url_string,
                  "css_class": "",
                  "required": 1,
                  "editable": 0,
                  "key": "title",
                  "hidden": 0,
                  "type": "StringField"
                },
                "my_monitoring_status": {
                  "description": "",
                  "title": "Monitoring Status",
                  "default": {jio_key: gadget.state.jio_key},
                  "css_class": "",
                  "required": 1,
                  "editable": 0,
                  "url": "gadget_slapos_installation_status.html",
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
                [['my_monitoring_status'], ["my_url_string"], ["my_reference"], ["my_aggregate_title"],
                ["my_aggregate_reference"], ["my_software_release_title"], ["my_software_release_version"],
                 ["my_state"], ["my_usage"]]
              ], [ "center",
                  []
              ]]
            }
          });
        })
        .push(function () {
          return gadget.getUrlFor({command: "change", options: {"page": "slap_destroy_software_installation"}});
        })
        .push(function (url) {
          var header_dict = {
            page_title: "Software Installation : " + gadget.state.doc.software_release_title,
            delete_url: url
          };
          return gadget.updateHeader(header_dict);
        });
    });
}(window, rJS, RSVP, jIO, Blob));