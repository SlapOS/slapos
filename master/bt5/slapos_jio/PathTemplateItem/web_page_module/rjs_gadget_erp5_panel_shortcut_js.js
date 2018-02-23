/*global window, rJS */
/*jslint nomen: true, indent: 2, maxerr: 3 */
(function (window, rJS) {
  "use strict";

  rJS(window)
    /////////////////////////////////////////////////////////////////
    //
    //  This is a sample minimalist gadget to be overwritten on project
    //  level to include special links on the panel.
    //
    /////////////////////////////////////////////////////////////////
    .declareMethod('render', function (options) {
      return this.changeState(options);
    })

    .onStateChange(function () {
      var gadget = this;
      return gadget;
    });

}(window, rJS));