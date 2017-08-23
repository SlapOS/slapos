/*global document, window, Option, rJS, RSVP, Chart, UriTemplate*/
/*jslint nomen: true, indent: 2, maxerr: 3 */
(function (window, rJS, RSVP) {
  "use strict";

  rJS(window)
    .ready(function (gadget) {
      gadget.property_dict = {};
      return gadget.getElement()
        .push(function (element) {
          gadget.property_dict.element = element;
          gadget.property_dict.deferred = RSVP.defer();
        });
    })
    /////////////////////////////////////////////////////////////////
    // Acquired methods
    /////////////////////////////////////////////////////////////////
    .declareAcquiredMethod("jio_getAttachment", "jio_getAttachment")
    .declareAcquiredMethod("translateHtml", "translateHtml")
    .declareAcquiredMethod("redirect", "redirect")
    .declareAcquiredMethod("updateHeader", "updateHeader")
    .declareAcquiredMethod("updateConfiguration", "updateConfiguration")
    .declareAcquiredMethod("getSetting", "getSetting")
    .declareAcquiredMethod("getUrlFor", "getUrlFor")
    .declareAcquiredMethod("jio_allDocs", "jio_allDocs")
    .declareAcquiredMethod("jio_get", "jio_get")

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
                url: "gadget_slapos_site_status.html",
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

    .allowPublicAcquisition("updateHeader", function () {
      return;
    })

    /////////////////////////////////////////////////////////////////
    // declared methods
    /////////////////////////////////////////////////////////////////
    .declareMethod("render", function () {
      var gadget = this;
      return new RSVP.Queue()
        .push(function () {
          var lines_limit, logout_url_template;

          return new RSVP.Queue()
            .push(function () {
              return RSVP.all([
                gadget.getSetting("listbox_lines_limit", 100),
                gadget.getSetting("me"),
                gadget.jio_getAttachment('acl_users', 'links')
              ]);
            })
            .push(function (settings) {
              lines_limit = settings[0];
              return RSVP.all([
                gadget.getDeclaredGadget('right'),
                gadget.jio_get(settings[1])
              ]);
            })
            .push(function (result) {
              var i, destination_list, column_list = [
                ['title', 'Title'],
                ['reference', 'Reference'],
                ['monitoring_status', 'Status']
              ];
              gadget.me_dict = result[1];
              destination_list = "%22NULL%22%2C";
              for (i in result[1].assignment_destination_list) {
                destination_list += "%22" + result[1].assignment_destination_list[i] + "%22%2C";
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
                      "key": "slap_site_listbox",
                      "lines": lines_limit,
                      "list_method": "portal_catalog",
                      "query": "urn:jio:allDocs?query=portal_type%3A%22" +
                        "Organisation" + "%22%20AND%20role_title%3A%22Host%22%20AND%20" +
                        "relative_url%3A(" + destination_list + ")",
                      "portal_type": [],
                      "search_column_list": column_list,
                      "sort_column_list": column_list,
                      "sort": [["title", "ascending"]],
                      "title": "Sites",
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
            });
        })
        .push(function () {
          var lines_limit;
          return new RSVP.Queue()
            .push(function () {
              return gadget.getSetting("listbox_lines_limit", 100);
            })
            .push(function (listbox_lines_limit) {
              lines_limit = listbox_lines_limit;
              return gadget.getDeclaredGadget('last');
            })
            .push(function (form_list) {
              var column_list = [
                ['title', 'Title'],
                ['reference', 'Reference'],
                ['translated_simulation_state_title', 'State']
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
                      "key": "slap_site_listbox",
                      "lines": lines_limit,
                      "list_method": "portal_catalog",
                      "query": "urn:jio:allDocs?query=portal_type%3A%20%28%22Support%20Request%22%2C%20%22Upgrade%20Decision%22%2C%20%22Regularisation%20Request%22%29%20AND%20destination_decision_reference%3A" +  gadget.me_dict.reference,
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
            });
        })
        .push(function () {
          return gadget.updateHeader({
            page_title: 'Dashboard'
          });
        });
    })
    .declareService(function () {
      var destination_list, gadget = this;
      return gadget.getSetting("me")
        .push(function (me) {
          return gadget.jio_get(me);
        })
        .push(function (person_doc) {
          var i;
          destination_list = '"NULL"';
          for (i in person_doc.assignment_destination_list) {
            destination_list += ' ,"' + person_doc.assignment_destination_list[i] + '"';
          }
          return gadget.jio_allDocs({
            query: "portal_type:Organisation AND role_title:Host AND relative_url:(" + destination_list + ")",
            select_list: ['title',
                          'reference',
                          'default_geographical_location_longitude',
                          'default_geographical_location_latitude']
          });
        })
        .push(function (result) {
          var idx, marker_list = [];
          for (idx in result.data.rows) {
            marker_list.push({
              "jio_key": result.data.rows[idx].id,
              "doc": {"title": result.data.rows[idx].value.title,
                      "reference": result.data.rows[idx].value.reference,
                      "latitude": result.data.rows[idx].value.default_geographical_location_latitude,
                      "longitude": result.data.rows[idx].value.default_geographical_location_longitude}
            });
          }
          return gadget.getElement()
            .push(function (element) {
              return gadget.declareGadget("gadget_erp5_page_map.html", {
                scope: "map",
                element: element.querySelector(".map-gadget")
              });
            })
            .push(function (map_gadget) {
              return map_gadget.render({
                zoom : 40,
                marker_list : marker_list
              });
            });
        });
    });
}(window, rJS, RSVP));