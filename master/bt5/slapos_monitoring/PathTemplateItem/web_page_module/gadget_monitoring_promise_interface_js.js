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
    ),
    load_history_template = Handlebars.compile(
      templater.getElementById("load-history-template").innerHTML
    );

  function formatDate(d){
    function addZero(n){
      return n < 10 ? '0' + n : '' + n;
    }

    return d.getFullYear() + "-" + addZero(d.getMonth()+1)
      + "-" + addZero(d.getDate()) + " " + addZero(d.getHours())
      + ":" + addZero(d.getMinutes()) + ":" + addZero(d.getSeconds());
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
              title: 'Monitoring Promise Result',
              //back_url: back_url,
              //panel_action: false,
              refresh_url: refresh_url
            })
          ]);
        })
        .push(function () {
          var jio_options = {
              type: "query",
              sub_storage: {
                type: "feed",
                feed_type: 'rss',
                url: options.jio_for.replace('share/jio_public/', 'public/feed'), // XXX keep compatibility!!
              }
            };
          gadget.property_dict.jio_gadget.createJio(jio_options);
          if (options.jio_name) {
            return gadget.property_dict.jio_gadget.allDocs({
              query: 'source: ' + options.jio_name,
              //include_docs: true              
            })
            .push(function (result_list) {
              if (result_list && result_list.data.total_rows > 0) {
                options.jio_key = result_list.data.rows[0].id;
              }
              return gadget.property_dict.jio_gadget.get(options.jio_key);
            });
          }
          return gadget.property_dict.jio_gadget.get(options.jio_key);
        })
        .push(function (feed) {
          var content,
            status,
            jio_options,
            element,
            promise_list = [];

          element = {
            status: feed.category,
            status_date: formatDate(new Date(feed.date)),
            monitor_href: feed.link,
            title: feed.source,
            hosting_subscription: feed.reference,
            "start-date": formatDate(new Date(feed.lastBuildDate)),
            instance: feed.siteTitle,
            public_url: feed.sourceUrl,
            message: feed.comments,
            type: 'status'
          };
          gadget.property_dict.promise_dict = element;

          return new RSVP.Queue()
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
              if (element.monitor_href) {
                jio_options = {
                  type: "query",
                  sub_storage: {
                    type: "drivetojiomapping",
                    sub_storage: {
                      type: "dav",
                      url: element.monitor_href
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
                warn = result[0].state.warning,
                fail = result[0].state.error,
                success = result[0].state.success,
                history_content,
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
                errors: fail + "/" + amount,
                warning: warn + "/" + amount,
                success: success + "/" + amount,
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
              history_content = history_widget_template({history_list: []});
              gadget.property_dict.element.querySelector("#promise-overview .ui-block-a")
                      .innerHTML += history_content;
            })
            .push(function () {
              return gadget.property_dict.render_deferred.resolve();
            });
        });
        /*
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
          })*/
    })
    .declareAcquiredMethod("updateHeader", "updateHeader")
    .declareAcquiredMethod('getUrlFor', 'getUrlFor')
    //.declareAcquiredMethod('loginRedirect', 'loginRedirect')
    .declareService(function () {
      var gadget = this,
        promise_list = [];

      promise_list.push(loopEventListener(
        gadget.property_dict.element.querySelector('.loadbox'),
        'click',
        false,
        function (evt) {
          return new RSVP.Queue()
            .push(function () {
              var text = gadget.property_dict.element.querySelector('.loadbox .loadwait a');
              $(".loadbox .signal").removeClass("ui-content-hidden");
              if (text) {
                text.textContent = "Loading...";
              }
            })
            .push(function () {
              var title = gadget.property_dict.promise_dict.title,
                jio_options,
                history_content;
    
              jio_options = {
                type: "query",
                sub_storage: {
                  type: "drivetojiomapping",
                  sub_storage: {
                    type: "dav",
                    url: gadget.property_dict.promise_dict.public_url
                  }
                }
              };
              gadget.property_dict.jio_gadget.createJio(jio_options, false);
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

                $(".loadbox .signal").addClass("ui-content-hidden");
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
                history_content = load_history_template({history_list: history_list});
                gadget.property_dict.element.querySelector(".loadbox")
                      .innerHTML = history_content;
                return $('.loadbox table').table().table("refresh");
              });
            });
        }
      ));

      return RSVP.all(promise_list);
    });


}(window, rJS, Handlebars, RSVP, $));