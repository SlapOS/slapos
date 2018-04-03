/*global window, rJS, RSVP, jIO, Blob */
/*jslint nomen: true, indent: 2, maxerr: 3 */
(function (window, rJS, RSVP, jIO, Blob) {
  "use strict";

  rJS(window)
    /////////////////////////////////////////////////////////////////
    // Acquired methods
    /////////////////////////////////////////////////////////////////
    .declareAcquiredMethod("updateHeader", "updateHeader")
    .declareAcquiredMethod("getSetting", "getSetting")
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
      // This code can cause problems if it is used more them once per
      // page
      param_list[0].sort_on = [["modification_date", "ascending"]];
      param_list[0].select_list = ["uid", "title", "text_content",
                                   "source_title", "modification_date", "content_type"];
      return gadget.jio_allDocs(param_list[0])
        .push(function (result) {
          var i, len = result.data.total_rows;
          for (i = 0; i < len; i += 1) {
            if (1 || (result.data.rows[i].value.hasOwnProperty("text_content"))) {
              result.data.rows[i].value.text_content = {
                css_class: "",
                description: "The Status",
                hidden: 0,
                "default": {doc: {title: result.data.rows[i].value.title,
                                  source: result.data.rows[i].value.source_title,
                                  modification_date: result.data.rows[i].value.modification_date,
                                  content_type: result.data.rows[i].value.content_type,
                                  text_content: result.data.rows[i].value.text_content}},
                key: "status",
                url: "gadget_slapos_event_discussion_entry.html",
                title: "Status",
                editable: 1,
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
          return gadget.getDeclaredGadget('form_view');
        })
        .push(function (form_gadget) {
          var editable = gadget.state.editable;
          var column_list = [
            ['text_content', 'Comments']
          ];
          return new RSVP.Queue()
            .push(function () {
              return gadget.getSetting("hateoas_url");
            })
           .push(function (hateoas_url) {
              return RSVP.all([
                gadget.getUrlFor({command: "change", options: {jio_key: gadget.state.doc.aggregate }})
              ]);
            })
            .push(function (result) {
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
                    "my_resource": {
                      "description": "The name of a document in ERP5",
                      "title": "Ticket Type",
                      "default": gadget.state.doc.resource_title,
                      "css_class": "",
                      "required": 1,
                      "editable": 0,
                      "key": "resource",
                      "hidden": 0,
                      "type": "StringField"
                    },
                    "my_aggregate_title": {
                      "description": "",
                      "title": "Related Computer or Service",
                      "default":
                        "<a href=" + result[0] + ">" +
                        gadget.state.doc.aggregate_title + "</a>",
                      "css_class": "",
                      "required": 1,
                      "editable": 0,
                      "key": "aggregate_title",
                      "hidden": (gadget.state.doc.aggregate_title === undefined) ? 1 : 0,
                      "type": "EditorField"
                    },
                    "my_simulation_state": {
                      "description": "",
                      "title": "State",
                      "default": gadget.state.doc.simulation_state_title,
                      "css_class": "",
                      "required": 1,
                      "editable": 0,
                      "key": "simulation_state",
                      "hidden": 0,
                      "type": "StringField"
                    },
                    "listbox": {
                      "column_list": column_list,
                      "show_anchor": 0,
                      "default_params": {},
                      "editable": 1,
                      "editable_column_list": [],
                      "key": "slap_ticket_event_listbox",
                      "lines": 10,
                      "list_method": "portal_catalog",
                      "query": "urn:jio:allDocs?query=portal_type%3A" +
                        "(%22Web Message%22, %22Mail Message%22)" + " AND default_follow_up_reference%3A" +
                        gadget.state.doc.reference,
                      "portal_type": [],
                      "search_column_list": [],
                      "sort_column_list": [],
                      "sort": [["text_content", "ascending"]],
                      "title": "",
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
                    [["my_title"], ["my_reference"], ["my_aggregate_title"]]
                  ], [
                    "right",
                    [["my_resource"], ["my_simulation_state"]]
                  ], [
                    "bottom",
                    [["listbox"]]
                  ]]
                }
              });
            });
        })
        .push(function () {
          return RSVP.all([
            gadget.getUrlFor({command: "change", options: {editable: true}}),
            gadget.getUrlFor({command: "change", options: {page: "slap_add_related_event", editable: true}}),
            gadget.getUrlFor({command: 'history_previous'})
          ]);
        })
        .push(function (url_list) {
          var header_dict = {
            page_title: "Support Request : " + gadget.state.doc.title,
            add_url: url_list[1],
            selection_url: url_list[2]
          };
          return gadget.updateHeader(header_dict);
        });
    });
}(window, rJS, RSVP, jIO, Blob));