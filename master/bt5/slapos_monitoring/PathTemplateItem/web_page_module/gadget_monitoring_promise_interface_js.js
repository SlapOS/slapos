/*global window, rJS, RSVP, Handlebars, $
    loopEventListener, btoa */
/*jslint nomen: true, indent: 2, maxerr: 3*/
(function (window, rJS, Handlebars, RSVP, $) {
  "use strict";

  var gadget_klass = rJS(window),
    templater = gadget_klass.__template_element,
    promise_widget_template = Handlebars.compile(
      templater.getElementById("promise-widget-template").innerHTML
    ),
    instance_widget_template = Handlebars.compile(
      templater.getElementById("pinstance-widget-template").innerHTML
    ),
    links_widget_template = Handlebars.compile(
      templater.getElementById("plinks-widget-template").innerHTML
    ),
    history_widget_template = Handlebars.compile(
      templater.getElementById("phistory-widget-template").innerHTML
    );

  function formatDate(d){
    function addZero(n){
      return n < 10 ? '0' + n : '' + n;
    }

    return d.getFullYear() + "-" + addZero(d.getMonth()+1)
      + "-" + addZero(d.getDate()) + " " + addZero(d.getHours())
      + ":" + addZero(d.getMinutes()) + ":" + addZero(d.getMinutes());
  }

  gadget_klass
    .ready(function (gadget) {
      return gadget.getElement()
        .push(function (element) {
          gadget.property_dict = {
            element: element,
            render_deferred: RSVP.defer()
          };
        });
    })
    .ready(function (gadget) {
      return gadget.getDeclaredGadget("jio_gadget")
        .push(function (jio_gadget) {
          gadget.property_dict.jio_gadget = jio_gadget;
        });
    })
    .ready(function (gadget) {
      return gadget.getDeclaredGadget('login_gadget')
        .push(function (login_gadget) {
          gadget.property_dict.login_gadget = login_gadget;
        });
    })
    /*.ready(function (gadget) {
      return gadget.getDeclaredGadget("chart0")
        .push(function (chart0) {
          gadget.property_dict.chart0 = chart0;
        });
    })*/
    /*.ready(function (gadget) {
      return gadget.getDeclaredGadget("chart1")
        .push(function (chart1) {
          gadget.property_dict.chart1 = chart1;
        });
    })*/
    .declareMethod('render', function (options) {
      var gadget = this,
        global_state,
        url_options = $.extend(true, {}, options);
        url_options.t = Date.now() / 1000 | 0;
      return gadget.getUrlFor(url_options)
        .push(function (refresh_url) {
          var back_url = '#page=main&t=' + (Date.now() / 1000 | 0);
          return RSVP.all([
            gadget.updateHeader({
              title: 'Promise ' + options.jio_key,
              //back_url: back_url,
              //panel_action: false,
              refresh_url: refresh_url
            })
          ]);
        })
        .push(function () {
          if (!options.jio_key.endsWith('.status')) {
            options.jio_key +=  '.status';
          }
          if (options.jio_for !== undefined && options.jio_for !== '') {
            // Load from defined url
            var jio_options = {
              type: "query",
              sub_storage: {
                type: "drivetojiomapping",
                sub_storage: {
                  type: "dav",
                  url: options.jio_for
                }
              }
            };
            gadget.property_dict.jio_gadget.createJio(jio_options);
            return gadget.property_dict.jio_gadget.get(options.jio_key);
          } else {
            return gadget.jio_get(options.jio_key);
          }
        })
        .push(function (element) {
          var content,
            status,
            jio_options,
            promise_list = [];

          return new RSVP.Queue()
            /*.push(function () {
              return gadget.property_dict.login_gadget.loginRedirect(
                element._links.monitor.href,
                options,
                element.instance,
                element.hosting_subscription
              );
            })*/
            .push(function () {
              status = (element.status.toLowerCase() === 'error') ? 
                'red' : (element.status.toLowerCase() === 'warning') ? 'warning' : 'ok';
              element.state = status;
              if (element['change-time']) {
                element.status_date = formatDate(new Date(element['change-time']*1000));
              }
              content = promise_widget_template({
                  element: element
                });
              gadget.property_dict.element.querySelector(".ui-promise-content .ui-promise-title h2")
                .innerHTML += element.hosting_subscription + ' > ' + element.instance + ' > ' + element.title;
              gadget.property_dict.element.querySelector("#promise-overview .ui-block-a")
                .innerHTML += content;
              if (element.hasOwnProperty('_links') && element._links.hasOwnProperty('monitor') && element._links.monitor.href) {
                jio_options = {
                  type: "query",
                  sub_storage: {
                    type: "drivetojiomapping",
                    sub_storage: {
                      type: "dav",
                      url: element._links.monitor.href,
                      //basic_login: cred.hash
                    }
                  }
                };
                gadget.property_dict.jio_gadget.createJio(jio_options);
                promise_list.push(gadget.property_dict.jio_gadget.get('monitor.global'));
              }
              return RSVP.all(promise_list);
            })
            .push(function (result) {
              var global_content,
                links_content,
                amount = 0,
                warn = result[0].state.warning*100,
                fail = result[0].state.error*100,
                success = result[0].state.success*100,
                tmp_process_url,
                tmp_url;

              global_state = result[0];

              // Ressource view Urls
              tmp_url = "#page=resource_view&title=" + global_state.title +
                "&root=" + global_state['hosting-title'] +
                "&jio_for=" + global_state._links.private_url.href;

              tmp_process_url = "#page=process_view&title=" + global_state.title +
                "&root=" + global_state['hosting-title'] +
                "&jio_for=" + global_state._links.private_url.href;

              amount = result[0].state.warning + result[0].state.error + result[0].state.success;
              global_content = instance_widget_template({
                title: result[0].title,
                root_title: result[0]['hosting-title'],
                status: result[0].status,
                date: result[0].date,
                errors: (fail/amount).toFixed(2),
                warning: (warn/amount).toFixed(2),
                success: (success/amount).toFixed(2),
                instance: result[0]._embedded.instance,
                resource_url: tmp_url,
                process_url: tmp_process_url
              });
              links_content = links_widget_template({
                public_url: result[0]._links.public_url.href,
                private_url: result[0]._links.private_url.href,
                rss_url: result[0]._links.rss_url.href
              });
              gadget.property_dict.element.querySelector("#promise-overview .ui-block-b")
                .innerHTML += global_content;
              gadget.property_dict.element.querySelector("#promise-overview .ui-block-a .promise-links")
                .innerHTML += links_content;
            })
            .push(function () {
              return gadget.property_dict.render_deferred.resolve();
            });
        })
        .push(function () {
          var title = options.jio_key.slice(0, -7),
            jio_options,
            history_content,
            jio_url = options.jio_for;

          jio_options = {
            type: "query",
            sub_storage: {
              type: "drivetojiomapping",
              sub_storage: {
                type: "dav",
                url: jio_url
              }
            }
          };
          gadget.property_dict.jio_gadget.createJio(jio_options);
          return gadget.property_dict.jio_gadget.get(title+'.history')
          .push(undefined, function (error) {
            console.log(error);
            return undefined;
          })
          .push(function (status_history) {
            var i,
              start_index = 0,
              history_size,
              history_list = [];

            if (status_history && status_history.hasOwnProperty('data')) {
              if (history_size > 200) {
                start_index = history_size - 200;
              }
              history_size = status_history.data.length;
              for (i = start_index; i < history_size; i += 1) {
                history_list.push(status_history.data[i]);
              }
              history_list.reverse();
            }
            history_content = history_widget_template({history_list: history_list});
            gadget.property_dict.element.querySelector("#promise-overview .ui-block-a")
                  .innerHTML += history_content;
          })/*
          .push(function () {
            return gadget.property_dict.login_gadget.loginRedirect(
              global_state._links.private_url.href,
              options,
              global_state.title,
              global_state['hosting-title']);
          })
          .push(function (cred) {
            var jio_options,
              jio_key = "monitor_state.data",
              data_url = global_state._links.private_url.href + 'data/';

            jio_options = {
              type: "query",
              sub_storage: {
                type: "drivetojiomapping",
                sub_storage: {
                  type: "dav",
                  url: data_url,
                  basic_login: cred.hash
                }
              }
            };
            gadget.property_dict.jio_gadget.createJio(jio_options, false);
            return gadget.property_dict.jio_gadget.get(jio_key);
          })
          .push(function (monitor_state) {
            var data = {
                labels: [],
                datasets: [
                  {
                    label: "SUCCESS",
                    fillColor: "rgba(21, 246, 21, 0)",
                    strokeColor: "rgba(21, 246, 21,1)",
                    pointColor: "rgba(21, 246, 21,1)",
                    pointStrokeColor: "#fff",
                    pointHighlightFill: "#fff",
                    pointHighlightStroke: "rgba(21, 246, 21,1)",
                    data: []
                  },
                  {
                    label: "ERROR",
                    fillColor: "rgba(255, 14, 44, 0)",
                    strokeColor: "rgba(255, 14, 44, 1)",
                    pointColor: "rgba(255, 14, 44, 1)",
                    pointStrokeColor: "#fff",
                    pointHighlightFill: "#fff",
                    pointHighlightStroke: "rgba(255, 14, 44, 1)",
                    data: []
                  },
                  {
                    label: "WARNING",
                    fillColor: "rgba(239, 196, 56,0)",
                    strokeColor: "rgba(239, 196, 56,1)",
                    pointColor: "rgba(239, 196, 56,1)",
                    pointStrokeColor: "#fff",
                    pointHighlightFill: "#fff",
                    pointHighlightStroke: "rgba(239, 196, 56,1)",
                    data: []
                  }
                ]
              },
              i,
              tmp,
              start = 0;
              
            if (monitor_state.hasOwnProperty('data')) {
              if (monitor_state.data.length > 20) {
                start = monitor_state.data.length - 20;
              }
              for (i = start; i < monitor_state.data.length; i += 1) {
                tmp = monitor_state.data[i].split(',');
                data.labels.push(tmp[0]);
                data.datasets[0].data.push(tmp[1]);
                data.datasets[1].data.push(tmp[2]);
                data.datasets[2].data.push(tmp[3]);
              }
            }
            return gadget.property_dict.chart1.render({
              type: 'line',
              config: {
                bezierCurve: false,
                responsive: true
              },
              data: data
            });
          })
          .push(function () {
            var data = {
              labels: [global_state.date],
              datasets: [
                {
                  label: "SUCCESS",
                  fillColor: "rgba(21, 246, 21, 0.7)",
                  strokeColor: "rgba(21, 246, 21,1)",
                  pointColor: "rgba(21, 246, 21,1)",
                  pointStrokeColor: "#fff",
                  pointHighlightFill: "#fff",
                  pointHighlightStroke: "rgba(21, 246, 21,1)",
                  data: [global_state.state.success],
                  name: "success"
                },
                {
                  label: "ERROR",
                  fillColor: "rgba(255, 14, 44, 0.7)",
                  strokeColor: "rgba(255, 14, 44, 1)",
                  pointColor: "rgba(255, 14, 44, 1)",
                  pointStrokeColor: "#fff",
                  pointHighlightFill: "#fff",
                  pointHighlightStroke: "rgba(255, 14, 44, 1)",
                  data: [global_state.state.error],
                  name: "error"
                },
                {
                  label: "WARNING",
                  fillColor: "rgba(239, 196, 56,0.7)",
                  strokeColor: "rgba(239, 196, 56,1)",
                  pointColor: "rgba(239, 196, 56,1)",
                  pointStrokeColor: "#fff",
                  pointHighlightFill: "#fff",
                  pointHighlightStroke: "rgba(239, 196, 56,1)",
                  data: [global_state.state.warning],
                  name: "warning"
                }
              ]
            };
            return gadget.property_dict.chart0.render({
              type: 'bar',
              config: {
                bezierCurve: false,
                responsive: true,
                barDatasetSpacing: 20
              },
              data: data
            });
          })*/;
        });
    })
    .declareAcquiredMethod("updateHeader", "updateHeader")
    .declareAcquiredMethod('getUrlFor', 'getUrlFor')
    //.declareAcquiredMethod('loginRedirect', 'loginRedirect')
    .declareAcquiredMethod("jio_get", "jio_get");


}(window, rJS, Handlebars, RSVP, $));