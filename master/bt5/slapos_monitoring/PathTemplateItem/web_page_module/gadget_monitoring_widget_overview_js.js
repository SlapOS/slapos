/*global window, rJS, RSVP, Handlebars, loopEventListener, $ */
/*jslint nomen: true, indent: 2 */
(function (window, rJS, RSVP, Handlebars, loopEventListener, $) {
  "use strict";

  /////////////////////////////////////////////////////////////////
  // templates
  /////////////////////////////////////////////////////////////////
  var gadget_klass = rJS(window),
    templater = gadget_klass.__template_element,

    header_listbox_widget = Handlebars.compile(
      templater.getElementById("header-widget-overview").innerHTML
    ),
    listbox_widget_template = Handlebars.compile(
      templater.getElementById("overview-widget-listview").innerHTML
    );

  /////////////////////////////////////////////////////////////////
  // some methods
  /////////////////////////////////////////////////////////////////

  gadget_klass

    /////////////////////////////////////////////////////////////////
    // ready
    /////////////////////////////////////////////////////////////////
    .ready(function (gadget) {
      gadget.property_dict = {
        render_deferred: RSVP.defer()
      };
    })

    .ready(function (gadget) {
      return gadget.getElement()
        .push(function (element) {
          gadget.property_dict.element = element;
          gadget.property_dict.filter_panel = $(gadget.property_dict.element.querySelector(".overview-filter-panel"));
        });
    })
    .ready(function (gadget) {
      return gadget.getDeclaredGadget("jio_gadget")
        .push(function (jio_gadget) {
          gadget.property_dict.jio_gadget = jio_gadget;
        });
    })
    .ready(function (gadget) {
      gadget.property_dict.filter_panel.panel({
        "position-fixed": true,
        "display": "overlay",
        "position": "right",
        "theme": "b"
      });
    })
    .ready(function (gadget) {
      return gadget.property_dict.filter_panel.trigger("create");
    })

    /////////////////////////////////////////////////////////////////
    // published methods
    /////////////////////////////////////////////////////////////////

    /////////////////////////////////////////////////////////////////
    // acquired methods
    /////////////////////////////////////////////////////////////////
    .declareAcquiredMethod("jio_get", "jio_get")
    .declareAcquiredMethod("jio_allDocs", "jio_allDocs")
    .declareAcquiredMethod("getUrlFor", "getUrlFor")
    .declareAcquiredMethod("translate", "translate")
    .declareAcquiredMethod("redirect", "redirect")
    .declareAcquiredMethod("getSetting", "getSetting")
    .declareAcquiredMethod("setSetting", "setSetting")

    /////////////////////////////////////////////////////////////////
    // declared methods
    /////////////////////////////////////////////////////////////////
    .declareMethod('render', function (option_dict) {
      var gadget = this,
        content = '',
        j,
        k,
        k_len,
        search_string = '',
        translated_column_list = [],
        all_document_list = [],
        filter_part_list = [],
        getPartialData;

      // Create the search query
      if (option_dict.search) {
        search_string = '(' + option_dict.column.select + ':"%' + option_dict.search + '%"' + ')';
        for (k = 0, k_len = option_dict.search_column_list.length; k < k_len; k += 1) {
          search_string  += ' OR (' + option_dict.search_column_list[k].select +
            ':"%' + option_dict.search + '%"' + ')';
        }
        if (option_dict.query.query) {
          option_dict.query.query = '(' + search_string + ') AND ' + option_dict.query.query;
        } else {
          option_dict.query.query = '(' + search_string+ ')';
        }
      }

      if (option_dict.filter && option_dict.filter !== '') {
        for (j = 0; j < option_dict.filter.split('+').length; j += 1) {
          filter_part_list.push('(status:"' + option_dict.filter.split('+')[j].toUpperCase() + '")');
        }
        if (option_dict.query.query) {
          option_dict.query.query += ' AND (' + filter_part_list.join(' OR ') + ')';
        } else {
          option_dict.query.query =  filter_part_list.join(' OR ');
        }
      }

      getPartialData = function(dav_url, key) {
        var jio_options = {
            type: "query",
            sub_storage: {
              type: "drivetojiomapping",
              sub_storage: {
                type: "dav",
                url: dav_url
              }
            }
          };
        gadget.property_dict.jio_gadget.createJio(jio_options);
        return gadget.property_dict.jio_gadget.allDocs(option_dict.query)
          .push(function (monitor_dict) {
            var i;
            if (monitor_dict && monitor_dict.data.total_rows > 0) {
              for (i = 0; i < monitor_dict.data.total_rows; i += 1) {
                if (monitor_dict.data.rows[i].id !== option_dict.data_id) {
                  continue;
                }
                all_document_list.push(monitor_dict.data.rows[i].value);
              }
            } else {
              // XXX
              console.log("Failed to get monitor.global at " + dav_url);
            }
            return;
          });
      };
      

      // store initial configuration
      gadget.property_dict.option_dict = option_dict;

      return new RSVP.Queue()
      .push(function () {
        return gadget.property_dict.jio_gadget.getMonitorUrlList();
      })
      .push(function (url_list) {
        var i,
          promise_list = [];
        for (i = 0; i < url_list.length; i += 1) {
          if (url_list[i]) {
            promise_list.push(getPartialData(url_list[i], option_dict.data_id));
          }
        }
        return RSVP.all(promise_list);
      })
      .push(function () {
        var promise_list = [],
          i_len,
          i;
        gadget.property_dict.document_list = all_document_list;
        for (i = 0, i_len = all_document_list.length; i < i_len; i += 1) {
          promise_list.push(gadget.getUrlFor({
            title: all_document_list[i].title,
            root_title: all_document_list[i]['hosting-title'],
            url: all_document_list[i]._links.monitor.href,
            page: 'software_instance_view'
          }));
        }

        return RSVP.all(promise_list);
      })
      .push(function (link_list) {
        var row_list = [],
          i_len,
          i,
          j_len,
          j;

        // build handlebars object
        for (j = 0, j_len = all_document_list.length; j < j_len; j += 1) {
          row_list.push({
            "href": link_list[j],
            "search": option_dict.search,
            "index": j,
            "date": all_document_list[j].date,
            "value": all_document_list[j].title,
            "hosting_value": all_document_list[j]['hosting-title'] || '',
            "status": all_document_list[j].hasOwnProperty('status') ? all_document_list[j].status.toLowerCase() : ''
          });
        }

        /*for (i = 0; i < option_dict.column_list.length; i += 1) {
          translated_column_list.push(gadget.translate(option_dict.column_list[i].title));
        }*/
        return RSVP.all([
          row_list,
          [
            {title: 'Status'},
            {title: 'Report Date'},
            {title: 'Software Instance'},
            {title: 'Hosting Subscription'}
          ]
        ]);
      })
      .push(function (result_list) {
        var header_content,
          sort_element,
          content = listbox_widget_template({
          row_list: result_list[0],
          column_list: result_list[1]
        });
        gadget.property_dict.element.querySelector(".ui-panel-overview .overview-content")
          .innerHTML += content;
        header_content = header_listbox_widget({
            widget_theme : option_dict.widget_theme,
            search: option_dict.search
          });
          gadget.property_dict.element.querySelector(".ui-panel-overview .overview-header")
            .innerHTML += header_content;
          if (option_dict.query.sort_on && option_dict.query.sort_on[0]) {
            sort_element = gadget.property_dict.element.querySelector('#listview-sort-' + option_dict.query.sort_on[0][0]);
            if (sort_element) {
              sort_element.checked = true;
            }
          }
      })
      .push(function () {
        return gadget.property_dict.render_deferred.resolve();
      });
    })

    /////////////////////////////////////////////////////////////////
    // declared service
    /////////////////////////////////////////////////////////////////
    .declareService(function () {
      var gadget = this;

      return new RSVP.Queue()
        .push(function () {
          return gadget.property_dict.render_deferred.promise;
        })
        .push(function () {
          var promise_list = [];
          promise_list.push(loopEventListener(
            gadget.property_dict.element.querySelector('form.search'),
            'submit',
            false,
            function (evt) {
              return gadget.redirect({
                page: gadget.property_dict.option_dict.search_page || '',
                sort_on: gadget.property_dict.option_dict.sort_on || '',
                search: evt.target[0].value,
                filter: gadget.property_dict.option_dict.filter || ''
              });
            })
          );
          promise_list.push(loopEventListener(
            gadget.property_dict.element.querySelector('.listview-filter'),
            'click',
            false,
            function (evt) {
              gadget.property_dict.filter_panel.panel("toggle");
            })
          );
          promise_list.push(loopEventListener(
            gadget.property_dict.element.querySelector('.listview-refresh'),
            'click',
            false,
            function (evt) {
              return gadget.redirect({
                page: gadget.property_dict.option_dict.search_page || '',
                sort_on: gadget.property_dict.option_dict.sort_on || '',
                search: gadget.property_dict.option_dict.search || '',
                filter: gadget.property_dict.option_dict.filter || '',
                t: Date.now() / 1000 | 0
              });
            })
          );
          promise_list.push(loopEventListener(
            gadget.property_dict.element.querySelector('form.filter'),
            'submit',
            false,
            function (evt) {
              var filter_status = [],
                element = gadget.property_dict.element;
              if (element.querySelector('#monitor-promise-error').checked) {
                filter_status.push('error');
              }
              if (element.querySelector('#monitor-promise-success').checked) {
                filter_status.push('ok');
              }
              if (element.querySelector('#monitor-promise-warning').checked) {
                filter_status.push('warning');
              }
              return gadget.redirect({
                page: gadget.property_dict.option_dict.search_page || '',
                sort_on: gadget.property_dict.option_dict.sort_on || '',
                search: gadget.property_dict.option_dict.search || '',
                filter: filter_status.join('+')
              });
            })
          );
          return RSVP.all(promise_list);
        });
    });

}(window, rJS, RSVP, Handlebars, loopEventListener, $));
