/*global window, rJS, RSVP, Handlebars, loopEventListener, $ */
/*jslint nomen: true, indent: 2 */
(function (window, rJS, RSVP, Handlebars, loopEventListener, $) {
  "use strict";

  /////////////////////////////////////////////////////////////////
  // templates
  /////////////////////////////////////////////////////////////////
  var gadget_klass = rJS(window),
    templater = gadget_klass.__template_element,
    hashCode = new Rusha().digestFromString;

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
    /*.ready(function (gadget) {
      return gadget.getSetting('instance_overview_selection')
        .push(function (selection) {
          gadget.property_dict.selection = selection || '';
        });
    })*/

    /////////////////////////////////////////////////////////////////
    // published methods
    /////////////////////////////////////////////////////////////////

    /////////////////////////////////////////////////////////////////
    // acquired methods
    /////////////////////////////////////////////////////////////////
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
        jio_options = {
          type: "query",
          sub_storage: {
            type: "drivetojiomapping",
            sub_storage: {
              type: "dav",
              url: option_dict.url
            }
          }
        },
        document_id = 'monitor.global';

      return new RSVP.Queue()
        .push(function () {
          gadget.property_dict.jio_gadget.createJio(jio_options);
          return gadget.property_dict.jio_gadget.get(
            document_id
          );
        })
        .push(function (current_document) {
          var instance_content,
            promise_list_template,
            content,
            promise_content,
            promise_list = [],
            i,
            tmp_url,
            tmp_process_url;

          gadget.property_dict.monitor = current_document;
          if (current_document.hasOwnProperty('data') &&
              current_document.data.hasOwnProperty('state')) {

            instance_content = Handlebars.compile(
              templater.getElementById("details-widget-overview").innerHTML
            ),
            promise_list_template = Handlebars.compile(
              templater.getElementById("promiselist-widget-template").innerHTML
            );

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
                error: current_document.state.error,
                success: current_document.state.success,
                instance: current_document._embedded.instance || '',
                public_url: current_document._links.hasOwnProperty('public_url') ? current_document._links.public_url.href : '',
                private_url: current_document._links.hasOwnProperty('private_url') ? current_document._links.private_url.href : '',
                rss_url: current_document._links.hasOwnProperty('rss_url') ? current_document._links.rss_url.href : '',
                resource_url: tmp_url,
                process_url: tmp_process_url,
                warning: (current_document.status.toUpperCase() === "WARNING") ? true : false
              });

              if (current_document._embedded.promises !== undefined) {
                for (i = 0; i < current_document._embedded.promises.length; i += 1) {
                  promise_list.push(current_document._embedded.promises[i]);
                  promise_list[i].href = "#page=view&jio_key=false&jio_name=" + 
                    promise_list[i].title + "&jio_for=" +
                    current_document._links.rss_url.href;
                  if (current_document.status === "WARNING") {
                    promise_list[i].status = current_document.status;
                  }
                }
              }
              promise_content = promise_list_template({
                promise_list: promise_list,
                date: current_document.date,
                short_date: new Date(current_document.date).toISOString().split('T')[0]
              });
            gadget.property_dict.element.querySelector(".overview-details")
              .innerHTML = content;
            gadget.property_dict.element.querySelector(".promise-list")
              .innerHTML = promise_content;
            return $(gadget.property_dict.element.querySelectorAll('fieldset[data-role="controlgroup"]'))
              .controlgroup().controlgroup('refresh');
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
          $(".graph-full .signal").removeClass("ui-content-hidden");
          return gadget.property_dict.login_gadget.getUrlInfo(
            hashCode(gadget.property_dict.monitor._links.private_url.href)
          )
          .push(function (cred) {
            if (cred === undefined) {
              cred == {};
            }
            var jio_options = {
                type: "query",
                sub_storage: {
                  type: "drivetojiomapping",
                  sub_storage: {
                    type: "dav",
                    url: gadget.property_dict.monitor._links.private_url.href + 'data/',
                    basic_login: cred.hash
                  }
                }
              };

            // Create online jio
            gadget.property_dict.jio_gadget.createJio(jio_options, false);
            return gadget.property_dict.jio_gadget.get(
              gadget.property_dict.monitor.data.state
            )
            .push(undefined, function (error) {
              console.log(error);
              return {};
            });
          });
        })
        .push(function (element_dict) {
          var promise_data = [
              "Date, Success, Error, Warning",
              new Date() + ",0,0,0"
            ],
            data = element_dict.data || promise_data;

          $(".graph-full .signal").addClass("ui-content-hidden");
          return gadget.property_dict.graph.render(
            data.join('\n'),
            {
              ylabel: '<span class="graph-label"><i class="fa fa-bar-chart"></i> Success/Failure count</span>',
              legend: 'always',
              labelsDivStyles: { 'textAlign': 'right' }
            },
            "customInteractionModel"
          );
        });
          //return RSVP.all(promise_list);
    });

}(window, rJS, RSVP, Handlebars, loopEventListener, $));
