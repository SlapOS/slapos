/*jslint nomen: true, indent: 2, maxerr: 3 */
/*global window, document, rJS, Handlebars, RSVP, Node, loopEventListener */
(function (window, document, rJS, Handlebars, RSVP, Node, loopEventListener) {
  "use strict";

  /////////////////////////////////////////////////////////////////
  // temlates
  /////////////////////////////////////////////////////////////////
  // Precompile templates while loading the first gadget instance
  var gadget_klass = rJS(window);

  gadget_klass
    .setState({
      visible: false,
      desktop: false
    })
    //////////////////////////////////////////////
    // acquired method
    //////////////////////////////////////////////
    .declareAcquiredMethod("getUrlFor", "getUrlFor")
    .declareAcquiredMethod("translateHtml", "translateHtml")
    .declareAcquiredMethod("getSetting", "getSetting")
    .declareAcquiredMethod("redirect", "redirect")

    /////////////////////////////////////////////////////////////////
    // declared methods
    /////////////////////////////////////////////////////////////////
    .declareMethod('toggle', function () {
      return this.changeState({
        visible: false
      });
    })
    .declareMethod('close', function () {
      return this.changeState({
        visible: false
      });
    })

    .declareMethod('render', function (options) {
      var erp5_document = options.erp5_document,
        workflow_list,
        view_list;
      if (erp5_document !== undefined) {
        workflow_list = erp5_document._links.action_workflow || [];
        view_list = erp5_document._links.action_object_view || [];
        if (workflow_list.constructor !== Array) {
          workflow_list = [workflow_list];
        }
        if (view_list.constructor !== Array) {
          view_list = [view_list];
        }
        // Prevent has much as possible to modify the DOM panel
        // stateChange prefer to compare strings
        workflow_list = JSON.stringify(workflow_list);
        view_list = JSON.stringify(view_list);
      }
      return this.changeState({
        workflow_list: workflow_list,
        view_list: view_list,
        global: true,
        editable: options.editable
      });
    })

    .onStateChange(function (modification_dict) {
      var context = this,
        gadget = this,
        queue = new RSVP.Queue(),
        tmp_element;

      return queue;
    })

    /////////////////////////////////////////////////////////////////
    // declared services
    /////////////////////////////////////////////////////////////////
    .onEvent('click', function (evt) {
      if ((evt.target.nodeType === Node.ELEMENT_NODE) &&
          (evt.target.tagName === 'BUTTON')) {
        return this.toggle();
      }
    }, false, false)

    .declareJob('listenResize', function () {
      // resize should be only trigger after the render method
      // as displaying the panel rely on external gadget (for translation for example)
      var result,
        event,
        context = this;
      function extractSizeAndDispatch() {
        if (window.matchMedia("(min-width: 90em)").matches) {
          return context.changeState({
            desktop: true
          });
        }
        return context.changeState({
          desktop: false
        });
      }
      result = loopEventListener(window, 'resize', false,
                                 extractSizeAndDispatch);
      event = document.createEvent("Event");
      event.initEvent('resize', true, true);
      window.dispatchEvent(event);
      return result;
    })

    .allowPublicAcquisition('notifyChange', function () {
      // Typing a search query should not modify the header status
      return;
    })
    .onEvent('submit', function () {
      var gadget = this;

      return gadget.getDeclaredGadget("erp5_searchfield")
        .push(function (search_gadget) {
          return search_gadget.getContent();
        })
        .push(function (data) {
          var options = {
            page: "search"
          };
          if (data.search) {
            options.extended_search = data.search;
          }
          // Remove focus from the search field
          document.activeElement.blur();
          return gadget.redirect({command: 'display', options: options});
        });

    }, false, true)

    .onEvent('blur', function (evt) {
      // XXX Horrible hack to clear the search when focus is lost
      // This does not follow renderJS design, as a gadget should not touch
      // another gadget content
      if (evt.target.type === 'search') {
        evt.target.value = "";
      }
    }, true, false);

}(window, document, rJS, Handlebars, RSVP, Node, loopEventListener));
