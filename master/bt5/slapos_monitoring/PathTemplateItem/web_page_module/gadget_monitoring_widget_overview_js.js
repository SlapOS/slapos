/*global window, rJS, RSVP, Handlebars, loopEventListener, $ */
/*jslint nomen: true, indent: 2 */
(function (window, rJS, RSVP, Handlebars, loopEventListener, $) {
  "use strict";

  /////////////////////////////////////////////////////////////////
  // templates
  /////////////////////////////////////////////////////////////////
  var gadget_klass = rJS(window),
    templater = gadget_klass.__template_element,

    listbox_widget_template = Handlebars.compile(
      templater.getElementById("overview-widget-listview").innerHTML
    ),
    header_listbox_widget = Handlebars.compile(
      templater.getElementById("header-widget-overview").innerHTML
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
          gadget.property_dict.block_index = 0;
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
      return gadget.getDeclaredGadget("graph_gadget")
        .push(function (graph_gadget) {
          gadget.property_dict.graph = graph_gadget;
        });
    })
    .ready(function (gadget) {
      return gadget.getDeclaredGadget("login_gadget")
        .push(function (login_gadget) {
          gadget.property_dict.login_gadget = login_gadget;
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
    .ready(function (gadget) {
      return gadget.getSetting('instance_overview_selection')
        .push(function (selection) {
          gadget.property_dict.selection = selection || '';
        });
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
        k,
        k_len,
        search_string = '',
        translated_column_list = [],
        all_document_list = [],
        monitor_url_list = [],
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
          option_dict.query.query = search_string;
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
            jio_key: all_document_list[i].id,
            jio_for: monitor_url_list[i],
            page: 'overview_details'
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
          [{title: 'Status'}, {title: 'Instance'}, {title: 'Hosting Subscription'}]
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
        return $(gadget.property_dict.element.querySelector(".ui-block-b .ui-panel-overview")).hide();
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
      
      function showInstanceDetails(element) {
        var jio_options = {
            type: "query",
            sub_storage: {
              type: "drivetojiomapping",
              sub_storage: {
                type: "dav"
              }
            }
          },
          index = parseInt($(element).attr('rel'), 10),
          private_link;

        if (!isNaN(index) && (gadget.property_dict.document_list.length > index)) {
          private_link = gadget.property_dict.document_list[index]._links.monitor.href;
        } else {
          return;
        }
        return new RSVP.Queue()
        .push(function () {
          $(".ui-block-b .signal").removeClass("ui-content-hidden");
          return gadget.setSetting('instance_overview_selection', private_link);
        })
        .push(function () {
          return gadget.property_dict.login_gadget.loginRedirect(
            private_link,
            {
              page: gadget.property_dict.option_dict.search_page || '',
              sort_on: gadget.property_dict.option_dict.sort_on || '',
              search: gadget.property_dict.option_dict.search || '',
              select: private_link
            },
            gadget.property_dict.document_list[index].title,
            gadget.property_dict.document_list[index]['hosting-title']
          );
        })
        .push(function (cred) {
          jio_options.sub_storage.sub_storage.url = private_link;
          jio_options.sub_storage.sub_storage.basic_login = cred.hash;
          gadget.property_dict.jio_gadget.createJio(jio_options);
          return gadget.property_dict.jio_gadget.get(
            gadget.property_dict.option_dict.data_id
          );
        })
        .push(function (current_document) {
          var instance_content,
            promise_list_template;

          if (current_document.hasOwnProperty('data') &&
              current_document.data.hasOwnProperty('state')) {

            jio_options.sub_storage.sub_storage.url = current_document._links.private_url.href + 'data/';
            instance_content = Handlebars.compile(
              templater.getElementById("details-widget-overview").innerHTML
            ),
            promise_list_template = Handlebars.compile(
              templater.getElementById("promiselist-widget-template").innerHTML
            );
            gadget.property_dict.jio_gadget.createJio(jio_options, false);
            return gadget.property_dict.jio_gadget.get(
                current_document.data.state
              )
              .push(function (element_dict) {
                $(gadget.property_dict.element.querySelector(".ui-block-b .ui-panel-overview")).show();
                return element_dict;
              })
              .push(function (element_dict) {
                var data = element_dict.data.join('\n'),
                  old_element = $(gadget.property_dict.element.querySelector('.ui-listview-container table td > a.selected'));

                if (old_element) {
                  old_element.removeClass('selected');
                }
                return gadget.property_dict.graph.render(
                  data,
                  {
                    xlabel: '<span class="graph-label"><i class="fa fa-bar-chart"></i> Promises Success/Failure Result</span>',
                    legend: 'always',
                    labelsDivStyles: { 'textAlign': 'right' }
                  },
                  "customInteractionModel"
                );
              })
              .push(function () {
                var content,
                  promise_content,
                  promise_list = [],
                  i,
                  tmp_url,
                  tmp_process_url;

                // Resource view URLs
                tmp_url = "#page=resource_view&title=" + current_document.title +
                  "&root=" + current_document['hosting-title'] +
                  "&jio_for=" + current_document._links.private_url.href;

                tmp_process_url = "#page=process_view&title=" + current_document.title +
                  "&root=" + current_document['hosting-title'] +
                  "&jio_for=" + current_document._links.private_url.href;

                content = instance_content({
                    title: current_document.title,
                    root_title: current_document['hosting-title'],
                    date: current_document.date,
                    status: current_document.status,
                    instance: current_document._embedded.instance || '',
                    public_url: current_document._links.hasOwnProperty('public_url') ? current_document._links.public_url.href : '',
                    private_url: current_document._links.hasOwnProperty('private_url') ? current_document._links.private_url.href : '',
                    rss_url: current_document._links.hasOwnProperty('rss_url') ? current_document._links.rss_url.href : '',
                    resource_url: tmp_url,
                    process_url: tmp_process_url
                  });

                  if (current_document._embedded.promises !== undefined) {
                    for (i = 0; i < current_document._embedded.promises.length; i += 1) {
                      promise_list.push(current_document._embedded.promises[i]);
                      promise_list[i].href = "#page=view&jio_key=" + 
                        promise_list[i].title + '.status' + "&jio_for=" +
                        current_document._links.public_url.href;
                    }
                  }
                  promise_content = promise_list_template({
                    promise_list: promise_list,
                    date: current_document.date
                  });
                $(element.querySelector('td:first-child > a')).addClass('selected');
                gadget.property_dict.element.querySelector(".overview-details")
                  .innerHTML = content;
                gadget.property_dict.element.querySelector(".promise-list")
                  .innerHTML = promise_content;
                $(".ui-block-b .signal").addClass("ui-content-hidden");
                return $(element.querySelectorAll('fieldset[data-role="controlgroup"]'))
                  .controlgroup().controlgroup('refresh');
              });
          }
          $(".ui-block-b .signal").addClass("ui-content-hidden");
          return false;
          
        });
      }
      
      return new RSVP.Queue()
        .push(function () {
          return gadget.property_dict.render_deferred.promise;
        })
        .push(function () {
          var promise_list = [],
            element_list = gadget.property_dict.element.querySelectorAll('.ui-listview-container table tr'),
            i;
          for (i = 0; i < element_list.length; i += 1) {
            promise_list.push(loopEventListener(
              element_list[i],
              'click',
              false,
              showInstanceDetails.bind(gadget, element_list[i])
            ));
          }
          promise_list.push(loopEventListener(
            gadget.property_dict.element.querySelector('form.search'),
            'submit',
            false,
            function (evt) {
              return gadget.redirect({
                jio_key: gadget.property_dict.option_dict.jio_key || '',
                page: gadget.property_dict.option_dict.search_page || '',
                sort_on: gadget.property_dict.option_dict.sort_on || '',
                search: evt.target[0].value
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
                status: filter_status.join('+')
              });
            })
          );
          if ( gadget.property_dict.selection) {
            for (i = 0; i < gadget.property_dict.document_list.length; i += 1) {
              if (gadget.property_dict.document_list[i]._links.monitor.href === gadget.property_dict.selection) {
                promise_list.push($(gadget.property_dict.element.querySelector(
                    '.ui-listview-container table tr[rel="' + i + '"]')
                  ).click());
                break;
              }
            }
          }
          return RSVP.all(promise_list);
        });
    });

}(window, rJS, RSVP, Handlebars, loopEventListener, $));
