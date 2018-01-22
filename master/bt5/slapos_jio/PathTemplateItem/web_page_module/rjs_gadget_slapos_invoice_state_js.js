/*globals console, window, rJS, RSVP, loopEventListener, i18n, Handlebars $*/
/*jslint indent: 2, nomen: true, maxlen: 80*/

(function (window, rJS, RSVP, Handlebars) {
  "use strict";
  var gadget_klass = rJS(window),
    payment_link_source = gadget_klass.__template_element
                         .getElementById("payment-link-template")
                         .innerHTML,
    payment_link_template = Handlebars.compile(payment_link_source),
    payment_state_source = gadget_klass.__template_element
                         .getElementById("payment-state-template")
                         .innerHTML,
    payment_state_template = Handlebars.compile(payment_state_source);

  gadget_klass
    .declareAcquiredMethod("jio_get", "jio_get")
    .declareAcquiredMethod("getSetting", "getSetting")
    .declareAcquiredMethod("jio_getAttachment", "jio_getAttachment")
    .declareAcquiredMethod("translateHtml", "translateHtml")

    .declareMethod("getContent", function () {
      return {};
    })
    .declareMethod("render", function (options) {
      var gadget = this;
      return new RSVP.Queue()
        .push(function () {
          return RSVP.all([
            gadget.getElement(),
            gadget.getSetting("hateoas_url")
          ]);
        })
        .push(function (result) {
          var hateoas_url = result[1],
              element = result[0];

          return gadget.jio_getAttachment(options.value.jio_key,
                hateoas_url +  options.value.jio_key +
                "/AccountingTransaction_getPaymentStateAsHateoas")
            .push(function (state) {
              console.log(state);
              var link, payment_transaction = state.payment_transaction;

              if (payment_transaction !== null) {
                link = payment_link_template({
                  invoice_state: state.state,
                  invoice_url: hateoas_url + payment_transaction +
                            "/PaymentTransaction_redirectToManualPayzenPayment"
                });
              } else {
                link = payment_state_template({
                  invoice_state: state.state
                });
              }
              element.innerHTML = link;
              return state;
            });
        });
    });
}(window, rJS, RSVP, Handlebars));