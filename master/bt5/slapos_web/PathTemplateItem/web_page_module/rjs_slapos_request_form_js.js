/*jslint nomen: true, maxlen: 200, indent: 2*/
/*global window, rJS , $ , console */
(function (window, rJS, $) {
  "use strict";

  var gk = rJS(window),
    json_url = "sample_schema.json", 
    parameter_gadget_url = "gadget_slapos_parameter_form.html";
    
  
  gk.declareMethod('getContent', function () {
    var g = this; 
    return g.getDeclaredGadget("parameter")
      .push(function(gadget) {
        var field_your_instance_xml = gadget.__element.querySelector('textarea[name=field_your_instance_xml]');
        if (field_your_instance_xml !== null) {
          return "SKIP";
        }
        return gadget.processValidation(g.options.json_url);
      })
      .push(function (xml_result) {
        if (xml_result === "SKIP") {
          /* The raw parameters are already on the request */
          return {};
        }
        return {"field_your_instance_xml": xml_result};
      })
      .fail(function (e) {
        return {};
      });
  });

  gk.declareMethod('render', function (options) {

    var g = this;

    options.json_url = "../../renderjs/slapos_load_schema_software_type.json";
    options.parameter = {};
    
    g.options = options;

    if (options.value !== undefined) {
      // A JSON where provided via gadgetfield
      $.extend(options, JSON.parse(options.value));
      delete options.value;
    }

    if (options.parameter.parameter_hash !== undefined) {
      // A JSON where provided via gadgetfield
      options.parameter.parameter_xml = atob(options.parameter.parameter_hash);
    }
    
    if (options.parameter.json_url !== undefined) {
      // A JSON where provided via gadgetfield
      options.json_url = options.parameter.json_url;
    }

    return g.declareGadget(parameter_gadget_url, {'scope': 'parameter'})
      .push(function (gadget) {
        return gadget.render(options);
      }).push(function (gadget) {
        var div = g.__element.querySelector(".parameter");
        $(div).replaceWith(gadget.__element);
        return gadget;
      });
  });

}(window, rJS, $));