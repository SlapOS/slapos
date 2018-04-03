/*global window, rJS, RSVP */
/*jslint nomen: true, indent: 2, maxerr: 3*/
(function (window, rJS, RSVP) {
  "use strict";

  rJS(window)
    .declareAcquiredMethod("updateHeader", "updateHeader")
    .declareAcquiredMethod("redirect", "redirect")
    .declareAcquiredMethod("reload", "reload")
    .declareAcquiredMethod("getSetting", "getSetting")
    .declareAcquiredMethod("jio_get", "jio_get")
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
                url: "gadget_slapos_project_status.html",
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
        lines_limit, destination_project_list;

      return new RSVP.Queue()
        .push(function () {
          return RSVP.all([
            gadget.getSetting("listbox_lines_limit", 20),
            gadget.getSetting("me")
          ]);
        })
        .push(function (settings) {
          lines_limit = settings[0];
          return RSVP.all([
            gadget.getDeclaredGadget('form_list'),
            gadget.jio_get(settings[1])
          ]);
        })
        .push(function (result) {
          var destination_project_list, i,
              column_list = [
            ['title', 'Title'],
            ['reference', 'Reference'],
            ['monitoring_status', 'Status']
          ];
          destination_project_list = "%22NULL%22%2C";
          for (i in result[1].assignment_destination_project_list) {
            destination_project_list += "%22" + result[1].assignment_destination_project_list[i] + "%22%2C";
          }
          return result[0].render({
            erp5_document: {
              "_embedded": {"_view": {
                "listbox": {
                  "column_list": column_list,
                  "show_anchor": 0,
                  "default_params": {},
                  "editable": 0,
                  "editable_column_list": [],
                  "key": "slap_project_listbox",
                  "lines": lines_limit,
                  "list_method": "portal_catalog",
                  // XXX TODO Filter by   default_strict_allocation_scope_uid="!=%s" % context.getPortalObject().portal_categories.allocation_scope.close.forever.getUid(),
                  "query": "urn:jio:allDocs?query=portal_type%3A%22" +
                    "Project" + "%22%20AND%20validation_state%3Avalidated%20AND%20" +
                    "relative_url%3A(" + destination_project_list + ")",
                  "portal_type": [],
                  "search_column_list": column_list,
                  "sort_column_list": column_list,
                  "sort": [["title", "ascending"]],
                  "title": "Projects",
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
            gadget.getUrlFor({command: "change", options: {"page": "slap_add_project"}}),
            gadget.getUrlFor({command: "change", options: {"page": "slapos"}})
          ]);
        })
        .push(function (result) {
          return gadget.updateHeader({
            page_title: "Projects",
            filter_action: true,
            selection_url: result[1],
            add_url: result[0]
          });
        });
    });
}(window, rJS, RSVP));