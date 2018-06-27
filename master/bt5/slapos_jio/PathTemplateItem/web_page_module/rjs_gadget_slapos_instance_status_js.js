/*globals console, window, rJS, RSVP, loopEventListener, i18n, Handlebars, $*/
/*jslint indent: 2, nomen: true, maxlen: 80*/

(function (window, rJS, RSVP, Handlebars) {
  "use strict";
  var gadget_klass = rJS(window),
    inline_status_source = gadget_klass.__template_element
                         .getElementById("inline-status-template")
                         .innerHTML,
    inline_status_template = Handlebars.compile(inline_status_source);

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

  function getStatus(gadget) {
    return  new RSVP.Queue()
      .push(function () {
        return gadget.jio_get(gadget.options.value.jio_key);
      })
      .push(function (result) {
        var status_class = 'ui-btn-no-data',
          status_title = 'Instance',
          status_style = "";

        status_class = checkInstanceStatus(result);
        if (status_class === 'ui-btn-no-data') {
          status_style = "color: transparent !important;";
        }

        gadget.element.innerHTML = inline_status_template({
          status_class: status_class,
          status_title: status_title,
          status_style: status_style
        });
        return gadget;
      });
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
    .declareJob("getStatus", function () {
      var gadget = this;
      return getStatus(gadget);
    })
    .onLoop(function () {
      var gadget = this;
      return getStatus(gadget);
    }, 300000)

    .declareMethod("render", function (options) {
      var gadget = this;
      gadget.options = options;
      gadget.flag = options.value.jio_key;
      return gadget.getStatus();
    });

}(window, rJS, RSVP, Handlebars));