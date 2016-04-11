/*global window, rJS, Chart, RSVP */
/*jslint nomen: true, indent: 2, maxerr: 3*/
(function (window, rJS, RSVP, Chart) {
  "use strict";

  rJS(window)

    .ready(function (gadget) {
      return gadget.getElement()
        .push(function (element) {
          gadget.property_dict = {
            element: element,
            render_deferred: RSVP.defer()
          };
        });
    })
    .ready(function (gadget) {
      // Initialize the gadget local parameters
      gadget.property_dict.ctx = gadget.property_dict.element.querySelector('canvas').getContext("2d");
      Chart.defaults.global = {
        // Boolean - Whether to animate the chart
        animation: true,
    
        // Number - Number of animation steps
        animationSteps: 60,
    
        // String - Animation easing effect
        // Possible effects are:
        // [easeInOutQuart, linear, easeOutBounce, easeInBack, easeInOutQuad,
        //  easeOutQuart, easeOutQuad, easeInOutBounce, easeOutSine, easeInOutCubic,
        //  easeInExpo, easeInOutBack, easeInCirc, easeInOutElastic, easeOutBack,
        //  easeInQuad, easeInOutExpo, easeInQuart, easeOutQuint, easeInOutCirc,
        //  easeInSine, easeOutExpo, easeOutCirc, easeOutCubic, easeInQuint,
        //  easeInElastic, easeInOutSine, easeInOutQuint, easeInBounce,
        //  easeOutElastic, easeInCubic]
        animationEasing: "easeOutQuart",
    
        // Boolean - If we should show the scale at all
        showScale: true,
    
        // Boolean - If we want to override with a hard coded scale
        scaleOverride: false,
    
        // ** Required if scaleOverride is true **
        // Number - The number of steps in a hard coded scale
        scaleSteps: null,
        // Number - The value jump in the hard coded scale
        scaleStepWidth: null,
        // Number - The scale starting value
        scaleStartValue: null,
    
        // String - Colour of the scale line
        scaleLineColor: "rgba(0,0,0,.1)",
    
        // Number - Pixel width of the scale line
        scaleLineWidth: 1,
    
        // Boolean - Whether to show labels on the scale
        scaleShowLabels: true,
    
        // Interpolated JS string - can access value
        scaleLabel: "<%=value%>",
    
        // Boolean - Whether the scale should stick to integers, not floats even if drawing space is there
        scaleIntegersOnly: true,
    
        // Boolean - Whether the scale should start at zero, or an order of magnitude down from the lowest value
        scaleBeginAtZero: false,
    
        // String - Scale label font declaration for the scale label
        scaleFontFamily: "'Helvetica Neue', 'Helvetica', 'Arial', sans-serif",
    
        // Number - Scale label font size in pixels
        scaleFontSize: 12,
    
        // String - Scale label font weight style
        scaleFontStyle: "normal",
    
        // String - Scale label font colour
        scaleFontColor: "#666",
    
        // Boolean - whether or not the chart should be responsive and resize when the browser does.
        responsive: true,
    
        // Boolean - whether to maintain the starting aspect ratio or not when responsive, if set to false, will take up entire container
        maintainAspectRatio: true,
    
        // Boolean - Determines whether to draw tooltips on the canvas or not
        showTooltips: true,
    
        // Function - Determines whether to execute the customTooltips function instead of drawing the built in tooltips (See [Advanced - External Tooltips](#advanced-usage-custom-tooltips))
        customTooltips: false,
    
        // Array - Array of string names to attach tooltip events
        tooltipEvents: ["mousemove", "touchstart", "touchmove"],
    
        // String - Tooltip background colour
        tooltipFillColor: "rgba(0,0,0,0.8)",
    
        // String - Tooltip label font declaration for the scale label
        tooltipFontFamily: "'Helvetica Neue', 'Helvetica', 'Arial', sans-serif",
    
        // Number - Tooltip label font size in pixels
        tooltipFontSize: 14,
    
        // String - Tooltip font weight style
        tooltipFontStyle: "normal",
    
        // String - Tooltip label font colour
        tooltipFontColor: "#fff",
    
        // String - Tooltip title font declaration for the scale label
        tooltipTitleFontFamily: "'Helvetica Neue', 'Helvetica', 'Arial', sans-serif",
    
        // Number - Tooltip title font size in pixels
        tooltipTitleFontSize: 14,
    
        // String - Tooltip title font weight style
        tooltipTitleFontStyle: "bold",
    
        // String - Tooltip title font colour
        tooltipTitleFontColor: "#fff",
    
        // Number - pixel width of padding around tooltip text
        tooltipYPadding: 6,
    
        // Number - pixel width of padding around tooltip text
        tooltipXPadding: 6,
    
        // Number - Size of the caret on the tooltip
        tooltipCaretSize: 8,
    
        // Number - Pixel radius of the tooltip border
        tooltipCornerRadius: 6,
    
        // Number - Pixel offset from point x to tooltip edge
        tooltipXOffset: 10,
    
        // String - Template string for single tooltips
        tooltipTemplate: "<%if (label){%><%=label%>: <%}%><%= value %>",
    
        // String - Template string for multiple tooltips
        multiTooltipTemplate: "<%= value %>",
    
        // Function - Will fire on animation progression.
        onAnimationProgress: function(){},
    
        // Function - Will fire on animation completion.
        onAnimationComplete: function(){}
      };
    })

    .declareMethod('render', function (options) {
      var gadget = this;
      gadget.property_dict.options = options;
      
    })
    .declareMethod('addData', function (valuesArray, label) {
      return gadget.property_dict.chart.addData(valuesArray, label);
    })
    .declareMethod('removeData', function () {
      return gadget.property_dict.chart.removeData();
    })
    .declareMethod('addDataIndex', function (segmentData, index) {
      return gadget.property_dict.chart.addData(segmentData, index);
    })
    .declareMethod('removeDataIndex', function (index) {
      return gadget.property_dict.chart.removeData(index);
    })
    .declareMethod('update', function () {
      return gadget.property_dict.chart.update();
    })
    .declareMethod('clear', function () {
      return gadget.property_dict.chart.clear();
    })
    .declareMethod('stop', function () {
      return gadget.property_dict.chart.stop();
    })
    .declareMethod('redraw', function () {
      return gadget.property_dict.chart.render();
    })
    .declareMethod('resize', function () {
      return gadget.property_dict.chart.resize();
    })
    .declareMethod('toBase64Image', function () {
      return gadget.property_dict.chart.toBase64Image();
    })
    .declareMethod('destroy', function () {
      return gadget.property_dict.chart.destroy();
    })
    .declareMethod('generateLegend', function () {
      return gadget.property_dict.chart.generateLegend();
    })

    .declareService(function () {
      var gadget = this;
      return new RSVP.Queue()
        .push(function () {
          var options = gadget.property_dict.options,
            promise_list = [];
          switch (options.type) {
            case "line": promise_list.push(
                new Chart(gadget.property_dict.ctx).Line(options.data, options.config)
              );
              break;
            case "bar": promise_list.push(
                new Chart(gadget.property_dict.ctx).Bar(options.data, options.config)
              );
              break;
            case "pie": promise_list.push(
                new Chart(gadget.property_dict.ctx).Pie(options.data, options.config)
              );
              break;
            case "doughnut": promise_list.push(
                new Chart(gadget.property_dict.ctx).Doughnut(options.data, options.config)
              );
              break;
            default: return [];
          }
          return new RSVP.Queue()
            .push(function () {
              return RSVP.all(promise_list);
            })
            .push(function (result_list) {
              gadget.property_dict.chart = result_list[0];
              gadget.property_dict.element.querySelector('.legend')
                .innerHTML += gadget.property_dict.chart.generateLegend();
              return gadget.property_dict.chart.render();
            });
        })
        .push(function () {
          var promise_list = [];
          promise_list.push(window.addEventListener("load", function () {
            console.log(gadget.property_dict.chart.generateLegend());
            return gadget.property_dict.chart.render();
          }));
          return RSVP.all(promise_list);
        });
    });


}(window, rJS, RSVP, Chart));
