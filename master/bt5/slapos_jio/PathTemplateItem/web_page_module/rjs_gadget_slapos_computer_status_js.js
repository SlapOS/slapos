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

  function checkComputerStatus(options) {
    if ((!options) || (options && !options.news)) {
      return 'ui-btn-no-data';
    }
    if (options.news.text.startsWith("#access")) {
      if (options.news.no_data_since_15_minutes) {
        return 'ui-btn-error';
      }
      if (options.news.no_data_since_5_minutes) {
        return 'ui-btn-warning';
      }
      return 'ui-btn-ok';

    } else {
      if (options.news.no_data) {
        return 'ui-btn-no-data';
      }
      return 'ui-btn-error';
    }
  }

  function checkComputerPartitionStatus(options) {
    var message,
        computer_partition,
        partition_class = 'ui-btn-ok',
        error_amount = 0,
        total_amount = 0;

    if ((!options) || (options && !options.computer_partition_news)) {
      return 'ui-btn-no-data';
    }

    for (computer_partition in options.computer_partition_news) {
      message = options.computer_partition_news[computer_partition].text;
      if (message.startsWith("#error")) {
        partition_class = 'ui-btn-warning';
        error_amount++;
      }
      total_amount++;

      if ((error_amount > 0) && (error_amount < total_amount)) {
        // No need to continue the result will be a warnning
        return partition_class;
      }
    }
    if (options.computer_partition === {}) {
      return 'ui-btn-no-data';
    }

    if (error_amount === total_amount) {
      // No need to continue the result will be a warnning
      return 'ui-btn-error';
    }
    return partition_class;
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

      function getComputerStatus(options) {
          queue.push(function () {
            return gadget.jio_get(options.value.jio_key);
            // return gadget.jio_get("computer_module/20171103-94D99B");
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
              monitor_url,
              status_class = 'ui-btn-no-data',
              status_title = 'Computer',
              right_title = 'Partitions',
              right_class = 'ui-btn-no-data',
              status_style = "color: transparent !important;",
              right_style = 'color: transparent !important;';

            if ((options.value !== undefined) && (options.doc === undefined)) {
              options.doc = options.value.doc;
            }
            status_class = checkComputerStatus(result);
            right_class = checkComputerPartitionStatus(result);

            i = options;
            // right_title = value.max? Math.round(value.max * 100 * 10) / 10 + '%': 'nan';
            right_style = '';
            status_style = '';

            template = inline_status_template;

            monitor_url = 'https://monitor.app.officejs.com/#/?page=ojsm_dispatch&query=portal_type%3A%22Software%20Instance%22%20AND%20aggregate_reference%3A' + result.reference;
            if (status_class === 'ui-btn-no-data') {
              status_style = "color: transparent !important;";
              //monitor_url = "";
            }

            gadget.element.innerHTML = template({
              monitor_url: monitor_url,
              status_class: status_class,
              status_title: status_title,
              status_style: status_style,
              middle_style: middle_style,
              right_class: right_class,
              right_title: right_title,
              right_style: right_style
            });
            return RSVP.delay(60000);
          })

          .push(function () {
            gadget.element.innerHTML = loading_template();
            return getComputerStatus(options);
          });
        }
      return queue.push(getComputerStatus(options));
    });
}(window, rJS, RSVP, Handlebars));