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

    .allowPublicAcquisition("jio_allDocs", function (param_list) {
      var gadget = this;
      return gadget.jio_allDocs(param_list[0])
        .push(function (result) {
          var i, value, len = result.data.total_rows;
          for (i = 0; i < len; i += 1) {
            if (1 || (result.data.rows[i].hasOwnProperty("id"))) {
              value = result.data.rows[i].id;
              result.data.rows[i].value.computer_monitoring_status = {
                css_class: "",
                description: "The Status",
                hidden: 0,
                "default": {jio_key: value},
                key: "status",
                url: "gadget_slapos_computer_status.html",
                title: "Status",
                type: "GadgetField"
              };
              result.data.rows[i].value["listbox_uid:list"] = {
                key: "listbox_uid:list",
                value: 2713
              };
            }
          }
          return result;
        });
    })

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
          return RSVP.all([
            gadget.getDeclaredGadget('form_view'),
            gadget.getSetting("hateoas_url")
          ]);
        })
        .push(function (result) {
          var editable = gadget.state.editable;
          var column_list = [
            ['title', 'Title'],
            ['reference', 'Reference'],
            ['computer_monitoring_status', 'Status']
          ];
          return result[0].render({
            erp5_document: {
              "_embedded": {"_view": {
                "my_title": {
                  "description": "",
                  "title": "Title",
                  "default": gadget.state.doc.title,
                  "css_class": "",
                  "required": 1,
                  "editable": editable,
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

                "my_default_geographical_location_longitude": {
                  "description": "",
                  "title": "Longitude",
                  "default": gadget.state.doc.default_geographical_location_longitude,
                  "css_class": "",
                  "required": 1,
                  "editable": 1,
                  "key": "default_geographical_location_longitude",
                  "hidden": 0,
                  "type": "FloatField"
                },

                "my_default_geographical_location_latitude": {
                  "description": "",
                  "title": "Latitude",
                  "default": gadget.state.doc.default_geographical_location_latitude,
                  "css_class": "",
                  "required": 1,
                  "editable": 1,
                  "key": "default_geographical_location_latitude",
                  "hidden": 0,
                  "type": "FloatField"
                },
                "my_monitoring_status": {
                  "description": "",
                  "title": "Map",
                  "default": {jio_key: gadget.state.jio_key},
                  "css_class": "",
                  "required": 1,
                  "editable": 0,
                  "url": "gadget_slapos_site_status.html",
                  "sandbox": "",
                  "key": "monitoring_status",
                  "hidden": 0,
                  "type": "GadgetField"
                },
                "my_organisation_map": {
                  "description": "",
                  "title": "Monitoring Status",
                  "default": [
                    {"jio_key": gadget.state.jio_key,
                     "doc": {"title": gadget.state.doc.title,
                            "reference": gadget.state.doc.reference,
                            "latitude": gadget.state.doc.default_geographical_location_latitude,
                            "longitude": gadget.state.doc.default_geographical_location_longitude}
                    }
                  ],
                  "css_class": "",
                  "required": 1,
                  "editable": 0,
                  "url": "gadget_slapos_computer_map.html",
                  "sandbox": "",
                  "key": "monitoring_status",
                  "hidden": 0,
                  "type": "GadgetField"
                },
                "listbox": {
                  "column_list": column_list,
                  "show_anchor": 0,
                  "default_params": {},
                  "editable": 0,
                  "editable_column_list": [],
                  "key": "slap_organisation_computer_listbox",
                  "lines": 10,
                  "list_method": "Organisation_getComputerTrackingList",
                  "list_method_template": result[1] + "ERP5Document_getHateoas?mode=search&" +
                            "list_method=Organisation_getComputerTrackingList&relative_url=" +
                            gadget.state.jio_key + "&default_param_json=eyJpZ25vcmVfdW5rbm93bl9jb2x1bW5zIjogdHJ1ZX0={&query,select_list*,limit*,sort_on*,local_roles*}",
                  "query": "urn:jio:allDocs?query=",
                  "portal_type": [],
                  "search_column_list": column_list,
                  "sort_column_list": column_list,
                  "sort": [["title", "ascending"]],
                  "title": "Associated Servers",
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
                [["my_title"], ["my_reference"], ['my_monitoring_status'],
                 ["my_default_geographical_location_longitude"],
                 ["my_default_geographical_location_latitude"]]
              ], [
                "right",
                [['my_organisation_map']]
              ], [
                "bottom",
                [["listbox"]]
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
          var header_dict = {
            selection_url: url_list[1],
            page_title: "Site : " + gadget.state.doc.title,
            save_action: true
          };
          if (!gadget.state.editable) {
            header_dict.edit_content = url_list[0];
          }
          return gadget.updateHeader(header_dict);
        });
    });
}(window, rJS, RSVP, jIO, Blob));