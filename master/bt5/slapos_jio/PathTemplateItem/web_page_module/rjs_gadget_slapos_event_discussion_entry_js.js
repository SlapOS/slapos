/*globals console, window, rJS, RSVP,  Handlebars, $*/
/*jslint indent: 2, nomen: true, maxlen: 80*/

(function (window, rJS, RSVP, Handlebars) {
  "use strict";
  var gadget_klass = rJS(window),
    inline_event_source = gadget_klass.__template_element
                         .getElementById("inline-event-template")
                         .innerHTML,
    inline_status_template = Handlebars.compile(inline_event_source),
    inline_html_event_source = gadget_klass.__template_element
                         .getElementById("inline-html-event-template")
                         .innerHTML,
    inline_html_status_template = Handlebars.compile(inline_event_source);


  gadget_klass
    .declareAcquiredMethod("getSetting", "getSetting")
    .declareAcquiredMethod("translateHtml", "translateHtml")
    .declareMethod("getContent", function () {
      return {};
    })
    .declareMethod("render", function (options) {
      var gadget = this,
        template = inline_status_template,
        source = options.value.doc.source,
        modification_date = options.value.doc.modification_date,
        text_content = options.value.doc.text_content,
        title = options.value.doc.title,
        content_type = options.value.doc.content_type;
      return new RSVP.Queue()
        .push(function () {
          if (content_type === 'text/html') {
            template = inline_html_status_template;
          }
          gadget.element.innerHTML = template({
            title: title,
            author: source,
            modification_date: modification_date,
            message: text_content
          });
        });
    });
}(window, rJS, RSVP, Handlebars));