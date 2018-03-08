/*global window, rJS, RSVP */
/*jslint nomen: true, indent: 2, maxerr: 3*/
(function (window, rJS, RSVP) {
  "use strict";

  rJS(window)
    .declareAcquiredMethod("updateHeader", "updateHeader")
    .declareAcquiredMethod("redirect", "redirect")
    .declareAcquiredMethod("reload", "reload")
    .declareAcquiredMethod("getSetting", "getSetting")
    .declareAcquiredMethod("setSetting", "setSetting")
    .declareAcquiredMethod("getUrlFor", "getUrlFor")
    .declareAcquiredMethod("jio_allDocs", "jio_allDocs")

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
                url: "gadget_slapos_network_status.html",
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

    /////////////////////////////////////////////////////////////////
    // declared methods
    /////////////////////////////////////////////////////////////////
    .declareMethod("triggerSubmit", function () {
      var argument_list = arguments;
      return this.getDeclaredGadget('form_list')
        .push(function (gadget) {
          return gadget.triggerSubmit.apply(gadget, argument_list);
        });
    })
    .declareMethod("render", function (options) {
      var gadget = this,
        lines_limit;

      return new RSVP.Queue()
        .push(function () {
          return gadget.getSetting("listbox_lines_limit", 20);
        })
        .push(function (listbox_lines_limit) {
          lines_limit = listbox_lines_limit;
          return gadget.getDeclaredGadget('form_list');
        })
        .push(function (form_list) {
          var column_list = [
            ['title', 'Title'],
            ['reference', 'Reference'],
            ['monitoring_status', 'Status']
          ];
          return form_list.render({
            erp5_document: {
              "_embedded": {"_view": {
                "listbox": {
                  "column_list": column_list,
                  "show_anchor": 0,
                  "default_params": {},
                  "editable": 0,
                  "editable_column_list": [],
                  "key": "slap_network_listbox",
                  "lines": lines_limit,
                  "list_method": "portal_catalog",
                  // Filter by My Own networks
                  "query": "urn:jio:allDocs?query=portal_type%3A%22" +
                    "Computer Network%22%20AND%20validation_state%3Avalidated",
                  "portal_type": [],
                  "search_column_list": column_list,
                  "sort_column_list": column_list,
                  "sort": [["reference", "ascending"]],
                  "title": "Network",
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
                "bottom",
                [["listbox"]]
              ]]
            }
          });
        })
        .push(function (result) {
          return RSVP.all([
            gadget.getUrlFor({command: "change", options: {"page": "slap_add_network"}})
          ]);
        })
        .push(function (result) {
          return gadget.updateHeader({
            page_title: "Networks",
            filter_action: true,
            add_url: result[0]
          });
        });
    });
}(window, rJS, RSVP));