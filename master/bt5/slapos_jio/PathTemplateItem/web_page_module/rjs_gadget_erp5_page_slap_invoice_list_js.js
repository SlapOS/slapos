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
            if (result.data.rows[i].value.hasOwnProperty("start_date")) {
              value = new Date(result.data.rows[i].value.start_date);
              result.data.rows[i].value.start_date = {
                allow_empty_time: 0,
                ampm_time_style: 0,
                css_class: "date_field",
                date_only: 1,
                description: "The Date",
                editable: 0,
                hidden: 0,
                hidden_day_is_last_day: 0,
                "default": value.toUTCString(),
                key: "date",
                required: 0,
                timezone_style: 0,
                title: "Status Date",
                type: "DateTimeField"
              };
            }

            if (result.data.rows[i].value.hasOwnProperty("total_price")) {
              value = window.parseFloat(result.data.rows[i].value.total_price);
              // The field seemms not set precision to display
              value = value.toFixed(2); // round on this case for 2 digits as
                                       // float field is bugged.
              result.data.rows[i].value.total_price = value;
            }
            if (1 || (result.data.rows[i].hasOwnProperty("id"))) {
              value = result.data.rows[i].id;
              result.data.rows[i].value.translated_simulation_state_title = {
                css_class: "",
                description: "Payment State",
                hidden: 0,
                "default": {jio_key: value},
                key: "translated_simulation_state_title",
                url: "gadget_slapos_invoice_state.html",
                title: "Payment State",
                type: "GadgetField"
              };
              result.data.rows[i].value.download = {
                css_class: "",
                description: "Download Invoice",
                hidden: 0,
                "default": {jio_key: value},
                key: "download",
                url: "gadget_slapos_invoice_printout.html",
                title: "Download",
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
            ['start_date', 'Date'],
            ['total_price', 'Price'],
            ['resource_reference', 'Currency'],
            ['translated_simulation_state_title', 'Payment'],
            ['download', 'Download']
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
                  "key": "slap_invoice_listbox",
                  "lines": lines_limit,
                  "list_method": "portal_catalog",
                  // XXX FIX ME: Missing default_destination_section_uid=person.getUid()
                  "query": "urn:jio:allDocs?query=(NOT%20title%3A%22Reversal%20Transaction%20for%20%25%22)%20AND%20(portal_type%3A%20%22Sale%20Invoice%20Transaction%22)",
                  "portal_type": [],
                  "search_column_list": column_list,
                  "sort_column_list": column_list,
                  "sort": [["creation_date", "descending"]],
                  "title": "Invoices",
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
            gadget.getUrlFor({command: "change", options: {"page": "slapos"}})
          ]);
        })
        .push(function (result) {
          return gadget.updateHeader({
            page_title: "Invoices",
            selection_url: result[0],
            filter_action: true
          });
        });
    });
}(window, rJS, RSVP));