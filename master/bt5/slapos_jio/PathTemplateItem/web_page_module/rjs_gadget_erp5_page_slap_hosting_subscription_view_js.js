/*global window, rJS, RSVP, jIO, Blob, btoa */
/*jslint nomen: true, indent: 2, maxerr: 3 */
(function (window, rJS, RSVP, jIO, Blob, btoa) {
  "use strict";

  rJS(window)
    /////////////////////////////////////////////////////////////////
    // Acquired methods
    /////////////////////////////////////////////////////////////////
    .declareAcquiredMethod("updateHeader", "updateHeader")
    .declareAcquiredMethod("getUrlParameter", "getUrlParameter")
    .declareAcquiredMethod("getUrlFor", "getUrlFor")
    .declareAcquiredMethod("getSetting", "getSetting")
    .declareAcquiredMethod("jio_getAttachment", "jio_getAttachment")
    .declareAcquiredMethod("jio_putAttachment", "jio_putAttachment")
    .declareAcquiredMethod("notifySubmitting", "notifySubmitting")
    .declareAcquiredMethod("notifySubmitted", 'notifySubmitted')
    .declareAcquiredMethod("jio_allDocs", 'jio_allDocs')

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
                hidden:  result.data.rows[i].value.portal_type === "Slave Instance",
                "default": {jio_key: value},
                key: "status",
                url: "gadget_slapos_instance_status.html",
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

    .declareMethod('updateDocument', function (param_list) {
      var gadget = this, property,
          content = param_list, doc = {};
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
      return gadget.getSetting("hateoas_url")
        .push(function (hateoas_url) {
          return gadget.jio_putAttachment(gadget.state.jio_key,
            hateoas_url + gadget.state.jio_key + "/HostingSubscription_edit", doc);
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
          return gadget.getDeclaredGadget('form_view');
        })
        .push(function (form_gadget) {
          var editable = gadget.state.editable;
          var column_list = [
            ['title', 'Title'],
            ['reference', 'Reference'],
            ['portal_type', 'Type'],
            ['computer_monitoring_status', 'Status']
          ], ticket_column_list = [
            ['title', 'Title'],
            ['reference', 'Reference'],
            ['modification_date', 'Modification Date'],
            ['translated_simulation_state_title', 'State']
          ], connection_column_list = [
              ['connection_key', 'Parameter'],
              ['connection_value', 'Value']
            ], parameter_dict = {
              'parameter' : {
                'json_url': gadget.state.doc.url_string + ".json",
                //'json_url': "https://lab.node.vifib.com/nexedi/slapos/raw/master/software/kvm/software.cfg.json",
                'parameter_hash': btoa('<?xml version="1.0" encoding="utf-8" ?><instance></instance>'),
                'restricted_softwaretype': false
              }
            };
          if (gadget.state.doc.text_content !== undefined) {
            parameter_dict.parameter.parameter_hash = btoa(gadget.state.doc.text_content);
          }
          return gadget.getSetting("hateoas_url")
            .push(function (url) {
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
                    "my_slap_state_title": {
                      "description": "",
                      "title": "State",
                      "default": gadget.state.doc.slap_state_title,
                      "css_class": "",
                      "required": 1,
                      "editable": 0,
                      "key": "slap_state_title",
                      "hidden": 0,
                      "type": "StringField"
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
                    "my_text_content": {
                      "description": "",
                      "title": "Configuration Parameter",
                      "default": parameter_dict,
                      "css_class": "",
                      "required": 1,
                      "editable": 1,
                      "url": "gadget_erp5_page_slap_parameter_form.html",
                      "sandbox": "",
                      "key": "text_content",
                      "hidden": 0,
                      "type": "GadgetField"
                    },
                    "my_monitoring_status": {
                      "description": "",
                      "title": "Monitoring Status",
                      "default": {jio_key: gadget.state.jio_key},
                      "css_class": "",
                      "required": 1,
                      "editable": 0,
                      "url": "gadget_slapos_hosting_subscription_status.html",
                      "sandbox": "",
                      "key": "monitoring_status",
                      "hidden": 0,
                      "type": "GadgetField"
                    },
                    "connection_listbox": {
                      "column_list": connection_column_list,
                      "show_anchor": 0,
                      "default_params": {},
                      "editable": 1,
                      "editable_column_list": [],
                      "key": "slap_connection_listbox",
                      "lines": 30,
                      "list_method": "HostingSubscription_getConnectionParameterList",
                      "list_method_template": url + "ERP5Document_getHateoas?mode=search&" +
                            "list_method=HostingSubscription_getConnectionParameterList&relative_url=" +
                            gadget.state.jio_key + "&default_param_json=eyJpZ25vcmVfdW5rbm93bl9jb2x1bW5zIjogdHJ1ZX0={&query,select_list*,limit*,sort_on*,local_roles*}",
                      "query": "urn:jio:allDocs?query=",
                      "portal_type": [],
                      "search_column_list": connection_column_list,
                      "sort_column_list": connection_column_list,
                      "sort": [["connection_key", "ascending"]],
                      "title": "Connection Parameters",
                      "type": "ListBox"
                    },
                    "ticket_listbox": {
                      "column_list": ticket_column_list,
                      "show_anchor": 0,
                      "default_params": {},
                      "editable": 1,
                      "editable_column_list": [],
                      "key": "slap_project_computer_listbox",
                      "lines": 10,
                      "list_method": "portal_catalog",
                      "query": "urn:jio:allDocs?query=%28%28portal_type%3A%22" +
                        "Support Request" + "%22%29%20AND%20%28" +
                        "default_aggregate_reference%3A%22" +
                        gadget.state.doc.reference + "%22%29%29",
                      "portal_type": [],
                      "search_column_list": ticket_column_list,
                      "sort_column_list": ticket_column_list,
                      "sort": [["title", "ascending"]],
                      "title": "Associated Tickets",
                      "type": "ListBox"
                    },
                    "listbox": {
                      "column_list": column_list,
                      "show_anchor": 0,
                      "default_params": {},
                      "editable": 1,
                      "editable_column_list": [],
                      "key": "slap_project_computer_listbox",
                      "lines": 10,
                      "list_method": "portal_catalog",
                      "query": "urn:jio:allDocs?query=%28portal_type%3A%28%22" +
                        "Slave Instance" + "%22%2C%20%22" +
                        "Software Instance" + "%22%29%20AND%20%28" +
                        "default_specialise_reference%3A%22" +
                        gadget.state.doc.reference + "%22%29%29",
                      "portal_type": [],
                      "search_column_list": column_list,
                      "sort_column_list": column_list,
                      "sort": [["title", "ascending"]],
                      "title": "Instances",
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
                    [["my_slap_state_title"], ["my_source_reference"]]
                  ], ["center",
                      [["my_url_string"], ["my_text_content"]]
                  ], [
                    "bottom",
                    [["connection_listbox"], ["listbox"], ["ticket_listbox"]]
                  ]]
                }
              });
            });
        })
        .push(function () {
          return RSVP.all([
            gadget.getUrlFor({command: "change", options: {editable: true}}),
            gadget.getUrlFor({command: "change", options: {"page": "slap_add_related_ticket"}}),
            gadget.getUrlFor({command: "change", options: {"page": "slap_start_hosting_subscription"}}),
            gadget.getUrlFor({command: "change", options: {"page": "slap_stop_hosting_subscription"}}),
            gadget.getUrlFor({command: "change", options: {"page": "slap_destroy_hosting_subscription"}}),
            gadget.getUrlFor({command: "change", options: {page: "slap_rss_ticket"}})

          ]);
        })
        .push(function (url_list) {
          var header_dict = {
            page_title: "Hosting Subscription: " + gadget.state.doc.title,
            ticket_url: url_list[1],
            destroy_url: url_list[4],
            rss_url: url_list[5],
            save_action: true
          };
          if (gadget.state.doc.slap_state === "start_requested") {
            header_dict.stop_url = url_list[3];
          }
          if (gadget.state.doc.slap_state === "stop_requested") {
            header_dict.start_url = url_list[2];
          }
          if (!gadget.state.editable) {
            header_dict.edit_content = url_list[0];
          }
          return gadget.updateHeader(header_dict);
        });
    });
}(window, rJS, RSVP, jIO, Blob, btoa));