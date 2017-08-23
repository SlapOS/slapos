/*globals console, window, rJS, RSVP, loopEventListener, i18n, Handlebars, $*/
/*jslint indent: 2, nomen: true, maxlen: 80*/

(function (window, rJS, RSVP, Handlebars) {
  "use strict";
  var gadget_klass = rJS(window),
    sensor_status_source = gadget_klass.__template_element
                         .getElementById("sensor-status-template")
                         .innerHTML,
    sensor_status_template = Handlebars.compile(sensor_status_source),
    inline_status_source = gadget_klass.__template_element
                         .getElementById("inline-status-template")
                         .innerHTML,
    inline_status_template = Handlebars.compile(inline_status_source),
    loading_source = gadget_klass.__template_element
                         .getElementById("loading-template")
                         .innerHTML,
    loading_template = Handlebars.compile(loading_source);

  function checkInstanceStatus(options) {
    if ((!options) || (options && !options.news)) {
      return 'ui-btn-no-data';
    }
    if (options.news.text.startsWith("#access")) {
      return 'ui-btn-ok';
    } else {
      if (options.no_data) {
        return 'ui-btn-no-data';
      }
      return 'ui-btn-error';
    }
  }

  gadget_klass
    .ready(function (gadget) {
      gadget.props = {};
      return gadget.getSetting("hateoas_url")
        .push(function (url) {
          gadget.props.hateoas_url = url;
        });
    })
    .declareAcquiredMethod("jio_get", "jio_get")
    .declareAcquiredMethod("getSetting", "getSetting")
    .declareAcquiredMethod("translateHtml", "translateHtml")

    .declareMethod("getContent", function () {
      return {};
    })
    .declareMethod("render", function (options) {
      var gadget = this,
        status_style,
        middle_style,
        queue = new RSVP.Queue();

      function getInstallationStatus(options) {
          queue.push(function () {
            return gadget.jio_get(options.value.jio_key);
          })
          .push(function (result) {
            var project,
              data_supply_line,
              data_supply_line_list,
              count = 0,
              tmp,
              sum = 0,
              i,
              no_data = true,
              no_data_since_24_hours = true,
              value = "",
              template,
              status_class = 'ui-btn-no-data',
              status_title = 'Instance',
              status_style = "color: transparent !important;";

            if ((options.value !== undefined) && (options.doc === undefined)) {
              options.doc = options.value.doc;
            }
            status_class = checkInstanceStatus(result);

            status_style = '';

            template = inline_status_template;

            if (status_class === 'ui-btn-no-data') {
              status_style = "color: transparent !important;";
            }

            gadget.element.innerHTML = template({
              status_class: status_class,
              status_title: status_title,
              status_style: status_style,
              middle_style: middle_style
            });
            return RSVP.delay(60000);
          })

          .push(function () {
            gadget.element.innerHTML = loading_template();
            return getInstallationStatus(options);
          });
        }
      return queue.push(getInstallationStatus(options));
    });
}(window, rJS, RSVP, Handlebars));