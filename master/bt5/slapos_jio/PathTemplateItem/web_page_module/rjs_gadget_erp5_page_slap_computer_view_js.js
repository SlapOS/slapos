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

    .allowPublicAcquisition("jio_allDocs", function (param_list) {
      var gadget = this;
      return gadget.jio_allDocs(param_list[0])
        .push(function (result) {
          var i, value, len = result.data.total_rows;
          for (i = 0; i < len; i += 1) {
            if (1 || (result.data.rows[i].hasOwnProperty("id"))) {
              value = result.data.rows[i].id;
              result.data.rows[i].value.monitoring_status = {
                css_class: "",
                description: "The Status",
                hidden: 0,
                "default": {jio_key: value},
                key: "status",
                url: "gadget_slapos_installation_status.html",
                title: "Status",
                type: "GadgetField"
              };
              result.data.rows[i].value.software_release = {
                css_class: "",
                description: "Software Release Info",
                hidden: 0,
                "default": {jio_key: value},
                key: "software_release",
                url: "gadget_slapos_software_release_info.html",
                title: "Software Release Info",
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
              var ndoc = gadget.state.doc;
              ndoc.allocation_scope = content.allocation_scope;
              return gadget.render({
                jio_key: gadget.state.jio_key,
                doc: ndoc
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

    .declareMethod("render", function (options) {
      var gadget = this, data;
      // Follow up changeState API but it is requires to actually
      // re-render the form to hide allocation scope
      gadget.state = {
        jio_key: options.jio_key,
        doc: options.doc,
        editable: 1
      };
      return new RSVP.Queue()
        .push(function () {
          return RSVP.all([
            gadget.getDeclaredGadget('form_view'),
            gadget.jio_allDocs({
              query: '(portal_type:"Computer Network")',
              sort_on: [['reference', 'ascending']],
              select_list: ['reference', 'title']
            })
          ]);
        })
        .push(function (results) {
          var editable = gadget.state.editable,
            form_gadget = results[0],
            computer_network_list = [["", ""]],
            column_list = [
              ['software_release', 'Software Release'],
              ['url_string', 'Url'],
              ['monitoring_status', 'Status']
            ],
            ticket_column_list = [
              ['title', 'Title'],
              ['reference', 'Reference'],
              ['modification_date', 'Modification Date'],
              ['translated_simulation_state_title', 'State']
            ],
            allocation_scope_list = [['', ''],
                                ['Closed for maintenance', 'close/maintenance'],
                                ['Closed for termination', 'close/termination'],
                                ['Closed forever', 'close/forever'],
                                ['Closed oudated', 'close/outdated'],
                                ['Open/Friend', 'open/friend'],
                                ['Open/Personal', 'open/personal'],
                                ['Open/Public', 'open/public']],
            i, value, len = results[1].data.total_rows;


          for (i = 0; i < len; i += 1) {
            computer_network_list.push([
              results[1].data.rows[i].value.title ? results[1].data.rows[i].value.title : results[1].data.rows[i].value.reference,
              results[1].data.rows[i].id
            ]);
          }

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
                "my_subordination": {
                  "description": "",
                  "title": "Network",
                  "default": gadget.state.doc.subordination,
                  "css_class": "",
                  "items": computer_network_list,
                  "required": 1,
                  "editable": 1,
                  "key": "subordination",
                  "hidden": 0,
                  "type": "ListField"
                },
                "my_allocation_scope": {
                  "description": "",
                  "title": "Allocation Scope",
                  "default": gadget.state.doc.allocation_scope,
                  "css_class": "",
                  "items": allocation_scope_list,
                  "required": 1,
                  "editable": 1,
                  "key": "allocation_scope",
                  "hidden": 0,
                  "type": "ListField"
                },
                "my_subject_list": {
                  "description": "",
                  "title": "Your Friends email",
                  "default": gadget.state.doc.subject_list,
                  "css_class": "",
                  "required": 1,
                  "editable": 1,
                  "key": "subject_list",
                  "hidden": (gadget.state.doc.allocation_scope === "open/friend") ? 0 : 1,
                  "type": "LinesField"
                },
                "my_source": {
                  "description": "The name of a document in ERP5",
                  "title": "Current Location",
                  "default": gadget.state.doc.source_title,
                  "css_class": "",
                  "required": 1,
                  "editable": 0,
                  "key": "",
                  "hidden": 0,
                  "type": "StringField"
                },
                "my_source_project": {
                  "description": "The name of a document in ERP5",
                  "title": "Current Project",
                  "default": gadget.state.doc.source_project_title,
                  "css_class": "",
                  "required": 1,
                  "editable": 0,
                  "key": "",
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
                  "url": "gadget_slapos_computer_status.html",
                  "sandbox": "",
                  "key": "monitoring_status",
                  "hidden": 0,
                  "type": "GadgetField"
                },
                "listbox": {
                  "column_list": column_list,
                  "show_anchor": 0,
                  "default_params": {},
                  "editable": 1,
                  "editable_column_list": [],
                  "key": "slap_software_installation_listbox",
                  "lines": 10,
                  "list_method": "portal_catalog",
                  "query": "urn:jio:allDocs?query=portal_type%3A%22" +
                    "Software Installation" + "%22%20AND%20default_aggregate_reference%3A" + gadget.state.doc.reference,
                  "portal_type": [],
                  "search_column_list": column_list,
                  "sort_column_list": column_list,
                  "sort": [["title", "ascending"]],
                  "title": "Supplied Softwares",
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
                [["my_title"], ["my_reference"], ["my_subordination"],
                 ['my_monitoring_status']]
              ], [
                "right",
                [["my_source"], ["my_source_project"], ["my_allocation_scope"], ["my_subject_list"]]
              ], [
                "bottom",
                [["ticket_listbox"], ["listbox"]]
              ]]
            }
          });
        })
        .push(function () {
          return RSVP.all([
            gadget.getUrlFor({command: "change", options: {editable: true}}),
            gadget.getUrlFor({command: "change", options: {"page": "slap_add_related_ticket"}}),
            gadget.getUrlFor({command: "change", options: {"page": "slap_select_software_product", 'computer_jio_key': gadget.state.jio_key}}),
            gadget.getUrlFor({command: "change", options: {page: "slap_computer_request_certificate"}}),
            gadget.getUrlFor({command: "change", options: {page: "slap_computer_revoke_certificate"}}),
            gadget.getUrlFor({command: "change", options: {page: "slap_rss_ticket"}}),
            gadget.getUrlFor({command: "change", options: {page: "slap_transfer_computer"}})
          ]);
        })
        .push(function (url_list) {
          var header_dict = {
            page_title: "Computer: " + gadget.state.doc.title,
            ticket_url: url_list[1],
            supply_url: url_list[2],
            request_certificate_url: url_list[3],
            revoke_certificate_url: url_list[4],
            rss_url: url_list[5],
            transfer_url: url_list[6],
            save_action: true
          };
          if (!gadget.state.editable) {
            header_dict.edit_content = url_list[0];
          }
          return gadget.updateHeader(header_dict);
        });
    });
}(window, rJS, RSVP, jIO, Blob));