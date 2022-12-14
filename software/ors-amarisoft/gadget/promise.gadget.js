/*global window, rJS, RSVP*/
/*jslint indent:2, maxlen:80, nomen:true */
(function () {
  "use strict";
  rJS(window)
    .declareAcquiredMethod("getPromiseDocument", "getPromiseDocument")
    .declareMethod("render", function (options) {
      var gadget = this;
      return gadget.getPromiseDocument(
        "check-cpu-temperature",
        "log/monitor/promise/check-cpu-temperature.json.log"
      )
        .push(function (result) {
          //gadget.element.textContent = result;
          result = result.replace(/\'/g,"\"");
          var item = result.split("\n"),
              tmp = "",
              data_tmp = "",
              data_list = [],
              time = [],
              data = [];
          item = JSON.parse(JSON.stringify(item));
          for(var i = 0; i < 30; i++)
          { 
            data_list.push(item[i]);
            var data_list_list = JSON.parse(data_list[i]);
            if (data_list_list.hasOwnProperty("time") 
                && data_list_list.hasOwnProperty("data")) {
              tmp = data_list_list.time.split(" ")[1].split(",")[0];
              data_tmp = data_list_list.data.cpu_temperature;
            }
            time.push(tmp);
            data.push(data_tmp);
            gadget.time = time;
            gadget.data = data;
          }

          var canvas = gadget.element.children.line,
              data = gadget.data, 
              label  = gadget.time,
              tooltip  = ['Twelve', 'Fifteen', 'Thirteen', 'Twenty-two', 'Eight', 'Twelve', 'Thirdy-one', 'Three', 'Five'];
          var line_chart = new LineChart(canvas, data, label, tooltip);
          line_chart.draw();
          line_chart.tooltipOn('mousemove');
        });
    });
    

  
}());