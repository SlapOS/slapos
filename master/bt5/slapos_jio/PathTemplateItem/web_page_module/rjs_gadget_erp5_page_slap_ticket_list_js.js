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
    .declareAcquiredMethod("jio_get", "jio_get")


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
          return RSVP.all([
            gadget.getSetting("listbox_lines_limit", 20),
            gadget.getSetting("me")
          ]);
        })
        .push(function (setting) {
          lines_limit = setting[0];
          return RSVP.all([
            gadget.getDeclaredGadget('form_list'),
            gadget.jio_get(setting[1])
          ]);
        })
        .push(function (result) {
          var column_list = [
            ['title', 'Title'],
            ['reference', 'Reference'],
            ['translated_simulation_state_title', 'State']
          ];
          return result[0].render({
            erp5_document: {
              "_embedded": {"_view": {
                "listbox": {
                  "column_list": column_list,
                  "show_anchor": 0,
                  "default_params": {},
                  "editable": 0,
                  "editable_column_list": [],
                  "key": "slap_site_listbox",
                  "lines": lines_limit,
                  "list_method": "portal_catalog",
                  "query": "urn:jio:allDocs?query=portal_type%3A%20%28%22Support%20Request%22%2C%20%22Upgrade%20Decision%22%2C%20%22Regularisation%20Request%22%29%20AND%20destination_decision_reference%3A" +  result[1].reference,
                  "portal_type": [],
                  "search_column_list": column_list,
                  "sort_column_list": column_list,
                  "sort": [["modification_date", "Descending"]],
                  "title": "Tickets",
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
            gadget.getUrlFor({command: "change", options: {"page": "slap_add_ticket"}}),
            gadget.getUrlFor({command: "change", options: {"page": "slap_rss_ticket"}}),
            gadget.getUrlFor({command: "change", options: {"page": "slapos"}})
          ]);
        })
        .push(function (result) {
          return gadget.updateHeader({
            page_title: "Tickets",
            filter_action: true,
            selection_url: result[2],
            add_url: result[0],
            rss_url: result[1]
          });
        });
    });
}(window, rJS, RSVP));