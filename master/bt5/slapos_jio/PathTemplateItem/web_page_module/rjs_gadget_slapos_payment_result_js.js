/*globals console, window, rJS, RSVP, loopEventListener, i18n, Handlebars $*/
/*jslint indent: 2, nomen: true, maxlen: 80*/

(function (window, rJS, RSVP, Handlebars) {
  "use strict";
  var gadget_klass = rJS(window),
    message_source = gadget_klass.__template_element
                         .getElementById("message-template")
                         .innerHTML,
    message_template = Handlebars.compile(message_source);

  gadget_klass
    .declareAcquiredMethod("jio_get", "jio_get")
    .declareAcquiredMethod("getSetting", "getSetting")
    .declareAcquiredMethod("jio_getAttachment", "jio_getAttachment")
    .declareAcquiredMethod("translateHtml", "translateHtml")
    .declareAcquiredMethod("getUrlFor", "getUrlFor")
    .declareAcquiredMethod("updateHeader", "updateHeader")


    .declareMethod("getContent", function () {
      return {};
    })
    .declareMethod("render", function (options) {
      var gadget = this;
      return new RSVP.Queue()
        .push(function () {
          return RSVP.all([
            gadget.getElement(),
            gadget.getUrlFor({command: 'change',
                     options: {jio_key: "/", page: "slap_invoice_list", "result": ""}})
          ]);
        })
        .push(function (result) {
          var payment_url = result[1],
              element = result[0],
              message, advice, page_title;
          if (options.result === "success") {
            page_title = "Thank you for your Payment";
            message = "Thank you for finalising the payment.";
            advice = "It will be processed by PayZen interface.";
          } else if (options.result === "cancel") {
            page_title = "Payment cancelled";
            message = "You have cancelled the payment process.";
            advice = "Please consider continuing it as soon as possible, otherwise you will be not able to use full functionality.";
          } else if (options.result === "error") {
            page_title = "Payment Error";
            message = "There was an error while processing the payment.";
            advice = "Please try again later or contact the support.";
          } else if (options.result === "referral") {
            page_title = "Payment Referral";
            message = "Your credit card was refused by payment system.";
            advice = "Please contact your bank or use another credit card.";
          } else if (options.result === "refused") {
            page_title = "Payment Refused";
            message = "The payment has been refused.";
            advice = "Please contact your bank.";
          } else if (options.result === "return") {
            page_title = "Payment Unfinished";
            message = "You have not finished your payment.";
            advice = "Please consider continuing it as soon as possible, otherwise you will be not able to use full functionality.";
          } else if (options.result === "already_registered") {
            page_title = "Payment already registered";
            message = "Your payment had already been registered.";
          } else {
            throw new Error("Unknown action to take: " + options.result);
          }
          console.log(options);
          element.innerHTML = message_template({
            message_to_acknowledge: message,
            advice: advice,
            payment_url: payment_url
          });
          return page_title;
        })
        .push(function (page_title) {
          var header_dict = {
            page_title: page_title
          };
          return gadget.updateHeader(header_dict);
        });
    });
}(window, rJS, RSVP, Handlebars));