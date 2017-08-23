/*globals console, window, rJS, RSVP,  Handlebars, $*/
/*jslint indent: 2, nomen: true, maxlen: 80*/

(function (window, rJS, RSVP, Handlebars) {
  "use strict";
  var gadget_klass = rJS(window),
    inline_event_source = gadget_klass.__template_element
                         .getElementById("inline-event-template")
                         .innerHTML,
    inline_status_template = Handlebars.compile(inline_event_source);


  gadget_klass
    .declareAcquiredMethod("getSetting", "getSetting")
    .declareAcquiredMethod("translateHtml", "translateHtml")
    .declareMethod("getContent", function () {
      return {};
    })
    .declareMethod("render", function (options) {
      var gadget = this,
        source = options.value.doc.source,
        modification_date = options.value.doc.modification_date,
        text_content = options.value.doc.text_content,
        title = options.value.doc.title,
        queue = new RSVP.Queue();
      console.log(options);
      return queue
        .push(function () {
          gadget.element.innerHTML = inline_status_template({
            title: title,
            author: source,
            modification_date: modification_date,
            message: text_content
          });
        });
    });
}(window, rJS, RSVP, Handlebars));