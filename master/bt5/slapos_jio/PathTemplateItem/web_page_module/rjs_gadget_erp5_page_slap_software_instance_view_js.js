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
    .declareAcquiredMethod("getSetting", "getSetting")
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
          var editable = gadget.state.editable;
          var column_list = [
            ['title', 'Title'],
            ['reference', 'Reference'],
            ['computer_monitoring_status', 'Status']
          ],
            connection_column_list = [
              ['connection_key', 'Parameter'],
              ['connection_value', 'Value']
            ];
          return new RSVP.Queue()
           .push(function () {
              return RSVP.all([
                gadget.getUrlFor({command: "change", options: {jio_key: gadget.state.doc.specialise }}),
                gadget.getSetting("hateoas_url")
              ]);
            })
            .push(function (url_list) {
              return form_gadget.render({
                erp5_document: {
                  "_embedded": {"_view": {
                    "my_title": {
                      "description": "",
                      "title": "Title",
                      "default": gadget.state.doc.title,
                      "css_class": "",
                      "required": 1,
                      "editable": 0,
                      "key": "title",
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
                      "key": "reference",
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
                      "url": "gadget_slapos_instance_status.html",
                      "sandbox": "",
                      "key": "monitoring_status",
                      "hidden": gadget.state.doc.portal_type === "Slave Instance",
                      "type": "GadgetField"
                    },
                    "my_url_string": {
                      "description": "",
                      "title": "Software Release",
                      "default":
                        "<a target=_blank href=" + gadget.state.doc.url_string + ">" +
                        gadget.state.doc.url_string + "</a>",
                      "css_class": "",
                      "required": 1,
                      "editable": 0,
                      "key": "url_string",
                      "hidden": 0,
                      "type": "EditorField"
                    },
                    "my_specialise_title": {
                      "description": "",
                      "title": "Hosting Subscription",
                      "default":
                        "<a href=" + url_list[0] + ">" +
                        gadget.state.doc.specialise_title + "</a>",
                      "css_class": "",
                      "required": 1,
                      "editable": 0,
                      "key": "specialise_title",
                      "hidden": 0,
                      "type": "EditorField"
                    },
                    "my_source_reference": {
                      "description": "",
                      "title": "Software Type",
                      "default": gadget.state.doc.source_reference,
                      "css_class": "",
                      "required": 1,
                      "editable": 0,
                      "key": "source_reference",
                      "hidden": 0,
                      "type": "StringField"
                    },
                    "my_text_content": {
                      "description": "",
                      "title": "Instance Parameters",
                      "default": gadget.state.doc.text_content,
                      "css_class": "",
                      "required": 1,
                      "editable": 0,
                      "key": "text_content",
                      "hidden": 0,
                      "type": "TextareaField"
                    },
                    "connection_listbox": {
                      "column_list": connection_column_list,
                      "show_anchor": 0,
                      "default_params": {},
                      "editable": 1,
                      "editable_column_list": [],
                      "key": "slap_connection_listbox",
                      "lines": 10,
                      "list_method": "SoftwareInstance_getConnectionParameterList",
                      "list_method_template": url_list[1] + "ERP5Document_getHateoas?mode=search&" +
                        "list_method=SoftwareInstance_getConnectionParameterList&relative_url=" +
                        gadget.state.jio_key + "&default_param_json=eyJpZ25vcmVfdW5rbm93bl9jb2x1bW5zIjogdHJ1ZX0={&query,select_list*,limit*,sort_on*,local_roles*}",
                      "query": "urn:jio:allDocs?query=",
                      "portal_type": [],
                      "search_column_list": connection_column_list,
                      "sort_column_list": connection_column_list,
                      "sort": [["connection_key", "ascending"]],
                      "title": "Connection Parameters",
                      "type": "ListBox"
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
                    [["my_title"], ["my_reference"], ['my_monitoring_status']]
                  ], [
                    "right",
                    [["my_specialise_title"], ["my_source_reference"]]
                  ], [
                    "center",
                    [["my_url_string"], ["my_text_content"]]
                  ], [
                    "bottom",
                    [["connection_listbox"]]
                  ]]
                }
              });
            });
        })
        .push(function () {
          return RSVP.all([
            gadget.getUrlFor({command: "change", options: {editable: true}}),
            gadget.getUrlFor({command: 'history_previous'})
          ]);
        })
        .push(function (url_list) {
          var header_dict = {
            selection_url: url_list[1],
            page_title: gadget.state.doc.portal_type +
              " : " + gadget.state.doc.title
          };
          if (!gadget.state.editable) {
            header_dict.edit_content = url_list[0];
          }
          return gadget.updateHeader(header_dict);
        });
    });
}(window, rJS, RSVP, jIO, Blob));