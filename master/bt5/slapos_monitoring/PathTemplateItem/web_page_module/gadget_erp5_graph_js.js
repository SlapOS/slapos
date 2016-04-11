/*global window, rJS, console, RSVP, Dygraph */
/*jslint indent: 2, maxerr: 3 */
(function(rJS) {
  "use strict";

  // Custom Interaction Model for synchronised graphs
  var customInteractionModel = Dygraph.Interaction.defaultModel;

  customInteractionModel.touchend = function(event, g, context) {
    Dygraph.Interaction.endTouch(event, g, context);
    var viewWindow = g.xAxisRange();
    g.getFunctionOption("zoomCallback").call(g, viewWindow[0], viewWindow[1], g.yAxisRanges());

  };

  /*customInteractionModel.touchmove = function(event, g, context) {
    Dygraph.Interaction.moveTouch(event, g, context);
    var viewWindow = g.xAxisRange();
    g.getFunctionOption("zoomCallback").call(g, viewWindow[0], viewWindow[1], g.yAxisRanges());

  };

  customInteractionModel.mousemove = function(event, g, context) {
    if (context.isPanning) {
       var viewWindow = g.xAxisRange();
      g.getFunctionOption("zoomCallback").call(g, viewWindow[0], viewWindow[1], g.yAxisRanges());
    }
  }*/

  customInteractionModel.mouseup = function(event, g, context) {
    if (context.isPanning) {
       var viewWindow = g.xAxisRange();
      g.getFunctionOption("zoomCallback").call(g, viewWindow[0], viewWindow[1], g.yAxisRanges());
    }
  };

  rJS(window)

    /////////////////////////////////////////////////////////////////
    // ready
    /////////////////////////////////////////////////////////////////

    .ready(function(gadget) {
      gadget.property_dict = {};
      return gadget.getElement()
        .push(function(element) {
          gadget.property_dict.element = element;
        });
    })

    /////////////////////////////////////////////////////////////////
    // declared methods
    /////////////////////////////////////////////////////////////////

    .declareMethod('getColors', function() {
      var gadget = this;
      return new RSVP.Queue()
        .push(function () {
          return gadget.property_dict.graph.getColors();
        });
    })

    .declareMethod('setVisibility', function(num, value) {
      var gadget = this;
      return new RSVP.Queue()
        .push(function () {
          return gadget.property_dict.graph.setVisibility(num, value);
        });
    })

    .declareMethod('updateOptions', function(options, ndarray) {
      var gadget = this;
      return new RSVP.Queue()
        .push(function () {
          gadget.property_dict.graph.ndarray = ndarray;
          return gadget.property_dict.graph.updateOptions(options);
        });
    })

    .declareMethod('resize', function(width, height) {
      var gadget = this;
      return new RSVP.Queue()
        .push(function () {
          return gadget.property_dict.graph.resize(width, height);
        });
    })

    // render gadget
    .declareMethod('render', function(data, option_dict, interactionModel) {
      var gadget = this;
      if (interactionModel === "customInteractionModel") {
        option_dict.interactionModel = customInteractionModel;
      }
      return new RSVP.Queue()
        .push(function () {
          gadget.property_dict.graph = new Dygraph(
            gadget.property_dict.element,
            data,
            option_dict
          );
          return gadget;
        });
    });

}(rJS));