/*jslint nomen: true, maxlen: 200, indent: 2*/
/*global rJS, console, window, document, RSVP, btoa, atob, $, XMLSerializer, jQuery, URI, vkbeautify */

(function (window, document, rJS, $, XMLSerializer, jQuery, vkbeautify) {
  "use strict";

  var gk = rJS(window);

  function jsonDictToParameterXML(json) {
    var parameter_id,
      xml_output = $($.parseXML('<?xml version="1.0" encoding="utf-8" ?><instance />'));
    // Used by serialisation XML
    for (parameter_id in json) {
      if (json.hasOwnProperty(parameter_id)) {
        $('instance', xml_output).append(
          $('<parameter />', xml_output)
            .text(json[parameter_id])
              .attr({id: parameter_id})
        );
      }
    }
    return vkbeautify.xml(
      (new XMLSerializer()).serializeToString(xml_output.context)
    );
  }

  function jsonDictToParameterJSONInXML(json) {
    var xml_output = $($.parseXML('<?xml version="1.0" encoding="utf-8" ?><instance />'));
      // Used by serialisation XML
    $('instance', xml_output).append(
      $('<parameter />', xml_output)
          .text(vkbeautify.json(JSON.stringify(json)))
            .attr({id: "_"})
    );
    return vkbeautify.xml(
      (new XMLSerializer()).serializeToString(xml_output.context)
    );
  }

  function loopEventListener(target, type, useCapture, callback,
                             prevent_default) {
    //////////////////////////
    // Infinite event listener (promise is never resolved)
    // eventListener is removed when promise is cancelled/rejected
    //////////////////////////
    var handle_event_callback,
      callback_promise;

    if (prevent_default === undefined) {
      prevent_default = true;
    }

    function cancelResolver() {
      if ((callback_promise !== undefined) &&
          (typeof callback_promise.cancel === "function")) {
        callback_promise.cancel();
      }
    }

    function canceller() {
      if (handle_event_callback !== undefined) {
        target.removeEventListener(type, handle_event_callback, useCapture);
      }
      cancelResolver();
    }
    function itsANonResolvableTrap(resolve, reject) {
      var result;
      handle_event_callback = function (evt) {
        if (prevent_default) {
          evt.stopPropagation();
          evt.preventDefault();
        }

        cancelResolver();

        try {
          result = callback(evt);
        } catch (e) {
          result = RSVP.reject(e);
        }

        callback_promise = result;
        new RSVP.Queue()
          .push(function () {
            return result;
          })
          .push(undefined, function (error) {
            if (!(error instanceof RSVP.CancellationError)) {
              canceller();
              reject(error);
            }
          });
      };

      target.addEventListener(type, handle_event_callback, useCapture);
    }
    return new RSVP.Promise(itsANonResolvableTrap, canceller);
  }

  function render_selection(json_field, default_value) {
    var input = document.createElement("select"),
      option = document.createElement("option"),
      option_index,
      optionz;
    input.size = 1;
    option.value = "";
    if (default_value === undefined) {
      option.selected = "selected";
    }
    input.appendChild(option);
    for (option_index in json_field['enum']) {
      if (json_field['enum'].hasOwnProperty(option_index)) {
        optionz = document.createElement("option");
        optionz.value = json_field['enum'][option_index];
        optionz.textContent = json_field['enum'][option_index];
        if (json_field['enum'][option_index] === default_value) {
          optionz.selected = "selected";
        }
        input.appendChild(optionz);
      }
    }
    return input;
  }

  function render_textarea(json_field, default_value, data_format) {
    var input = document.createElement("textarea");
    if (default_value !== undefined) {
      if (default_value instanceof Array) {
        input.value = default_value.join("\n");
      } else {
        input.value = default_value;
      }
    }
    input["data-format"] = data_format;
    return input;
  }

  function render_field(json_field, default_value) {

    if (json_field['enum'] !== undefined) {
      return render_selection(json_field, default_value);
    }

    if (json_field.type === "boolean") {
      json_field['enum'] = [true, false];
      if (default_value === "true") {
        default_value = true;
      }
      if (default_value === "false") {
        default_value = false;
      }
      return render_selection(json_field, default_value);
    }

    if (json_field.type === "array") {
      return render_textarea(json_field, default_value, "array");
    }

    if (json_field.type === "string" && json_field.textarea === true) {
      return render_textarea(json_field, default_value, "string");
    }

    var input = document.createElement("input");

    if (default_value !== undefined) {
      input.value = default_value;
    }

    if (json_field.type === "integer") {
      input.type = "number";
    } else {
      input.type = "text";
    }

    return input;
  }

  function render_subform(json_field, default_dict, root, path) {
    var div_input,
      key,
      div,
      label,
      input,
      default_value,
      default_used_list = [],
      default_div,
      span_error,
      span_info;

    if (default_dict === undefined) {
      default_dict = {};
    }

    if (path === undefined) {
      path = "/";
    }

    if (json_field.patternProperties !== undefined) {
      if (json_field.patternProperties['.*'] !== undefined) {

        div = document.createElement("div");
        div.setAttribute("class", "subfield");
        div.title = json_field.description;

        /* console.log(key); */

        div_input = document.createElement("div");

        div_input = document.createElement("div");
        div_input.setAttribute("class", "input");

        input = document.createElement("input");
        input.type = "text";
        div_input.appendChild(input);

        input = document.createElement("button");
        input.value = btoa(JSON.stringify(json_field.patternProperties['.*']));
        input.setAttribute("class", "add-sub-form");
        input.type = "button";
        input.name = path;
        input.textContent = "Add";
        div_input.appendChild(input);

        div.appendChild(div_input);

        for (default_value in default_dict) {
          if (default_dict.hasOwnProperty(default_value)) {
            default_div = document.createElement("div");
            default_div.setAttribute("class", "slapos-parameter-dict-key");
            label = document.createElement("label");
            label.textContent = default_value;
            label.setAttribute("class", "slapos-parameter-dict-key");
            default_div.appendChild(label);
            default_div = render_subform(
              json_field.patternProperties['.*'],
              default_dict[default_value],
              default_div,
              path + "/" + default_value);
            div.appendChild(default_div);
          }
        }
        root.appendChild(div);

        return div;
      }
    }

    for (key in json_field.properties) {
      if (json_field.properties.hasOwnProperty(key)) {
        div = document.createElement("div");
        div.setAttribute("class", "subfield");
        div.title = json_field.properties[key].description;
        /* console.log(key); */
        label = document.createElement("label");
        label.textContent = json_field.properties[key].title;
        div.appendChild(label);
        div_input = document.createElement("div");
        div_input.setAttribute("class", "input");
        if (json_field.properties[key].type === 'object') {
          div_input = render_subform(json_field.properties[key],
            default_dict[key],
            div_input,
            path + "/" + key);
        } else {
          input = render_field(json_field.properties[key], default_dict[key]);
          input.name = path + "/" + key;
          input.setAttribute("class", "slapos-parameter");
          div_input.appendChild(input);
        }
        default_used_list.push(key);
        if (json_field.properties[key]['default'] !== undefined) {
          span_info = document.createElement("span");
          span_info.textContent = '(default = ' + json_field.properties[key]['default'] + ')';
          div_input.appendChild(span_info);
        }
        span_error = document.createElement("span");
        span_error.setAttribute("class", "error");
        div_input.appendChild(span_error);
        div.appendChild(div_input);
        root.appendChild(div);
      }
    }
    for (key in default_dict) {
      if (default_dict.hasOwnProperty(key)) {
        if (default_used_list.indexOf(key) < 0 ) {
          div = document.createElement("div");
          div.setAttribute("class", "subfield");
          div.title = key;
          label = document.createElement("label");
          label.textContent = key;
          div.appendChild(label);
          div_input = document.createElement("div");
          div_input.setAttribute("class", "input");
          input = render_field({"type": "string"}, default_dict[key]);
          input.name = path + "/" + key;
          input.setAttribute("class", "slapos-parameter");
          div_input.appendChild(input);
        
          default_used_list.push(key);
          span_info = document.createElement("span");
          span_info.textContent = '(Not part of the schema)';
          div_input.appendChild(span_info);
          span_error = document.createElement("span");
          span_error.setAttribute("class", "error");
          div_input.appendChild(span_error);
          div.appendChild(div_input);
          root.appendChild(div);
        }
      }
    }
    return root;
  }

  function getFormValuesAsJSONDict(element) {
    var json_dict = {},
      entry,
      multi_level_dict = {};
    $(element.querySelectorAll(".slapos-parameter")).each(function (key, input) {
      if (input.value !== "") {
        if (input.type === 'number') {
          json_dict[input.name] = parseInt(input.value, 10);
        } else if (input.value === "true") {
          json_dict[input.name] = true;
        } else if (input.value === "false") {
          json_dict[input.name] = false;
        } else if (input.tagName === "TEXTAREA") {
          if (input["data-format"] === "string") {
            json_dict[input.name] = input.value;
          } else {
            json_dict[input.name] = input.value.split('\n');
          }
        } else {
          json_dict[input.name] = input.value;
        }
      }
    });

    function convertOnMultiLevel(key, value, d) {
      var i,
        kk,
        key_list = key.split("/");
      for (i = 2; i < key_list.length; i += 1) {
        kk = key_list[i];
        if (i === key_list.length - 1) {
          d[kk] = value;
        } else {
          if (!d.hasOwnProperty(kk)) {
            d[kk] = {};
          }
          d = d[kk];
        }
      }
    }

    for (entry in json_dict) {
      if (json_dict.hasOwnProperty(entry)) {
        convertOnMultiLevel(entry, json_dict[entry], multi_level_dict);
      }
    }

    return multi_level_dict;
  }

  function validateForm(gadget, json_url) {
    return gadget.processValidation(json_url);
  }

  function collapseParameter(element) {
    $(element).parent().children("div").toggle(300);
    if ($(element).hasClass("slapos-parameter-dict-key-colapse")) {
      $(element).removeClass("slapos-parameter-dict-key-colapse");
    } else {
      $(element).addClass("slapos-parameter-dict-key-colapse");
    }
    return element;
  }

  function addSubForm(element) {
    var subform_json = JSON.parse(atob(element.value)),
      input_text = element.parentNode.querySelector("input[type='text']"),
      div = document.createElement("div"),
      label;

    if (input_text.value === "") {
      return false;
    }

    div.setAttribute("class", "slapos-parameter-dict-key");
    label = document.createElement("label");
    label.textContent = input_text.value;
    label.setAttribute("class", "slapos-parameter-dict-key");
    div.appendChild(label);

    div = render_subform(subform_json, {}, div, element.name + "/" + input_text.value);

    element.parentNode.parentNode.insertBefore(div, element.parentNode.parentNode.children[1]);
    // element.parentNode.parentNode.appendChild(div);

    return div;
  }

  function loadEventList(gadget) {
    var g = gadget,
      field_list = g.props.element.querySelectorAll(".slapos-parameter"),
      button_list = g.props.element.querySelectorAll('button.add-sub-form'),
      label_list = g.props.element.querySelectorAll('label.slapos-parameter-dict-key'),
      i,
      promise_list = [];

    for (i = 0; i < field_list.length; i = i + 1) {
      promise_list.push(loopEventListener(
        field_list[i],
        'change',
        false,
        validateForm.bind(g, g, g.options.json_url)
      ));
    }

    for (i = 0; i < button_list.length; i = i + 1) {
      promise_list.push(loopEventListener(
        button_list[i],
        'click',
        false,
        addSubForm.bind(g, button_list[i])
      ));
    }

    for (i = 0; i < label_list.length; i = i + 1) {
      promise_list.push(loopEventListener(
        label_list[i],
        'click',
        false,
        collapseParameter.bind(g, label_list[i])
      ));
    }

    return RSVP.all(promise_list);
  }

  function getSoftwareTypeFromForm(element) {
    var input = element.querySelector(".slapos-software-type");

    if (input !== undefined && input !== null) {
      return input.value;
    }
    return "";
  }

  function getSerialisationTypeFromForm(element) {
    var input = element.querySelector(".slapos-serialisation-type");

    if (input !== undefined && input !== null) {
      return input.value;
    }
    return "";
  }

  gk.ready(function (g) {
    g.props = {};
    return g.getElement()
      .push(function (element) {
        g.props.element = element;
      });
  })

    .declareMethod("loadJSONSchema", function (url) {
      return this.getDeclaredGadget('loadschema')
        .push(function (gadget) {
          return gadget.loadJSONSchema(url);
        });
    })

    .declareMethod("validateJSONForSoftwareType", function (schema_url, softwaretype, generated_json) {
      return this.getDeclaredGadget('loadschema')
        .push(function (gadget) {
          return gadget.validateJSONForSoftwareType(schema_url, softwaretype, generated_json);
        });
    })

    .declareMethod("loadSoftwareJSON", function (url) {
      return this.getDeclaredGadget('loadschema')
        .push(function (gadget) {
          return gadget.loadSoftwareJSON(url);
        });
    })

    .declareAcquiredMethod('pleaseRedirectMyHash', 'pleaseRedirectMyHash')

    .declareMethod('processValidation', function (json_url) {
      var g = this,
        software_type = getSoftwareTypeFromForm(g.props.element),
        json_dict = getFormValuesAsJSONDict(g.props.element),
        serialisation_type = getSerialisationTypeFromForm(g.props.element);
      if (software_type === "") {
        if (g.options.parameter.shared) {
          throw new Error("The software type is not part of the json (" + software_type + " as slave)");
        }
        throw new Error("The software type is not part of the json (" + software_type + ")");
      }

      return g.validateJSONForSoftwareType(json_url, software_type, json_dict)
        .push(function (validation) {
          var error_index,
            parameter_hash_input = g.props.element.querySelectorAll('.parameter_hash_output')[0],
            field_name,
            div,
            divm,
            missing_index,
            missing_field_name,
            xml_output;

          $(g.props.element.querySelectorAll("span.error")).each(function (i, span) {
            span.textContent = "";
          });

          $(g.props.element.querySelectorAll("div.error-input")).each(function (i, div) {
            div.setAttribute("class", "");
          });
          if (serialisation_type === "json-in-xml") {
            xml_output = jsonDictToParameterJSONInXML(json_dict);
          } else {
            xml_output = jsonDictToParameterXML(json_dict);
          }
          parameter_hash_input.value = btoa(xml_output);
          // console.log(parameter_hash_input.value);
          if (validation.valid) {
            return xml_output;
          }
          for (error_index in validation.errors) {
            if (validation.errors.hasOwnProperty(error_index)) {
              field_name = validation.errors[error_index].dataPath;
              div = $(".slapos-parameter[name='/" + field_name  + "']")[0].parentNode;
              div.setAttribute("class", "slapos-parameter error-input");
              div.querySelector("span.error").textContent = validation.errors[error_index].message;
            }
          }

          for (missing_index in validation.missing) {
            if (validation.missing.hasOwnProperty(missing_index)) {
              missing_field_name = validation.missing[missing_index].dataPath;
              divm = $('.slapos-parameter[name=/' + missing_field_name  + "']")[0].parentNode;
              divm.setAttribute("class", "error-input");
              divm.querySelector("span.error").textContent = validation.missing[missing_index].message;
            }
          }
          return "ERROR";
        });
    })

    .declareMethod('renderParameterForm', function (json_url, default_dict) {

      var g = this;
      return g.loadJSONSchema(json_url)
        .push(function (json) {
          var fieldset_list = g.props.element.querySelectorAll('fieldset'),
            fieldset = document.createElement("fieldset");

          fieldset = render_subform(json, default_dict, fieldset);
          $(fieldset_list[1]).replaceWith(fieldset);
          return fieldset_list;
        });
    })

    .declareMethod('renderFailoverTextArea', function (content, error) {
      var g = this,
        div = document.createElement("div"),
        div_error = document.createElement("div"),
        span_error = document.createElement("span"),
        textarea = document.createElement("textarea"),
        fieldset = document.createElement("fieldset"),
        fieldset_list = g.props.element.querySelectorAll('fieldset'),
        button0 = g.props.element.querySelector("button.slapos-show-raw-parameter"),
        button1 = g.props.element.querySelector("button.slapos-show-form");

      if (button0 !== null) {
        $(button0).addClass("hidden-button");
      }

      if (button1 !== null) {
        $(button1).addClass("hidden-button");
      }

      div.setAttribute("class", "field");
      textarea.setAttribute("rows", "10");
      textarea.setAttribute("cols", "80");

      textarea.setAttribute("name", "field_your_instance_xml");
      textarea.textContent = content;

      span_error.setAttribute("class", "error");
      span_error.textContent = "You got one error when loading json schema, so the form is not going to be rendered: " + error;

      div_error.setAttribute("class", "error");

      div.appendChild(textarea);
      div_error.appendChild(span_error);
      div.appendChild(textarea);

      fieldset.appendChild(div);
      fieldset.appendChild(div_error);

      fieldset_list[0].innerHTML = '';
      $(fieldset_list[1]).replaceWith(fieldset);
      fieldset_list[2].innerHTML = '';

      return fieldset;
    })
    .declareMethod('renderRawParameterTextArea', function (content) {
      var g = this,
        div = document.createElement("div"),
        div_error = document.createElement("div"),
        textarea = document.createElement("textarea"),
        fieldset = document.createElement("fieldset"),
        fieldset_list = g.props.element.querySelectorAll('fieldset');

      div.setAttribute("class", "field");
      textarea.setAttribute("rows", "10");
      textarea.setAttribute("cols", "80");

      textarea.setAttribute("name", "field_your_instance_xml");
      textarea.textContent = content;

      div.appendChild(textarea);
      div.appendChild(textarea);

      fieldset.appendChild(div);
      fieldset.appendChild(div_error);

      $(fieldset_list[1]).replaceWith(fieldset);
      fieldset_list[2].innerHTML = '';

      return fieldset;
    })
    .declareMethod('render', function (options) {
      if (options.json_url === undefined) {
        throw new Error("undefined json_url");
      }
      var g = this,
        to_hide = g.props.element.querySelector("button.slapos-show-form"),
        to_show = g.props.element.querySelector("button.slapos-show-raw-parameter"),
        softwaretype;

      if (to_hide !== null) {
        $(to_hide).addClass("hidden-button");
      }

      if (to_show !== null) {
        $(to_show).removeClass("hidden-button");
      }


      this.options = options;

      return g.loadSoftwareJSON(g.options.json_url).push(function (json) {
        var option_index,
          option,
          option_selected = options.parameter.softwaretypeindex,
          restricted_softwaretype = options.parameter.restricted_softwaretype,
          input = g.props.element.querySelector('select.slapos-software-type'),
          parameter_shared = g.props.element.querySelector('input.parameter_shared'),
          s_input = g.props.element.querySelector('input.slapos-serialisation-type');

        if (options.parameter.softwaretypeindex === undefined) {
          option_selected = options.parameter.softwaretype;
        }

        if (input.children.length === 0) {
          for (option_index in json['software-type']) {
            if (json['software-type'].hasOwnProperty(option_index)) {
              option = document.createElement("option");
              if (json['software-type'][option_index]['software-type'] !== undefined) {
                option.value = json['software-type'][option_index]['software-type'];
              } else {
                option.value = option_index;
              }
              option['data-id'] = option_index;
              option.textContent = json['software-type'][option_index].title;
              // option.index = json['software-type'][option_index].index;

              if (options.parameter.shared === undefined) {
                options.parameter.shared = false;
              }

              if (option_selected === undefined) {
                option_selected = option_index;
                if (json['software-type'][option_index].shared === true) {
                  parameter_shared.value = true;
                } else {
                  parameter_shared.value = false;
                }
              }

              if (softwaretype === undefined) {
                softwaretype = option_selected;
              }

              if (json['software-type'][option_index].shared === undefined) {
                json['software-type'][option_index].shared = false;
              }

              option['data-shared'] = json['software-type'][option_index].shared;

              if ((option_index === option_selected) && 
                (options.parameter.shared === json['software-type'][option_index].shared)) {
                option.selected = "selected";
                if (json['software-type'][option_index].shared === true) {
                  parameter_shared.value = true;
                } else {
                  parameter_shared.value = false;
                }
              }

              if (restricted_softwaretype === true) {
                if (option.value === options.parameter.softwaretype) {
                  if (options.parameter.shared === json['software-type'][option_index].shared) {
                    input.appendChild(option);
                  }
                }
              } else {
                input.appendChild(option);
              }
            }
          }
        }
        
        

        if (softwaretype === undefined) {
          softwaretype = option_selected;
        }
        if (input.children.length === 0) {
          if (options.parameter.shared) {
            throw new Error("The software type is not part of the json (" + softwaretype + " as slave)");
          }
          throw new Error("The software type is not part of the json (" + softwaretype + ")");
        }
        if (json['software-type'][softwaretype] === undefined) {
          throw new Error("The sotware type is not part of the json (" + softwaretype + ")");
        }

        if (json['software-type'][softwaretype].serialisation !== undefined) {
          s_input.value = json['software-type'][softwaretype].serialisation;
          options.serialisation = json['software-type'][softwaretype].serialisation;
        } else {
          s_input.value = json.serialisation;
          options.serialisation = json.serialisation;
        }

        return json['software-type'][softwaretype].request;
      })
        .push(function (parameter_json_schema_url) {
          var parameter_dict = {}, json_url_uri, prefix, parameter_entry;

          if (options.parameter.parameter_xml !== undefined) {
            if (options.serialisation === "json-in-xml") {
              parameter_entry = jQuery.parseXML(
                options.parameter.parameter_xml
              ).querySelector("parameter[id='_']");
              if (parameter_entry !== null) {
                parameter_dict = JSON.parse(parameter_entry.textContent);
              }
            } else {
              $(jQuery.parseXML(options.parameter.parameter_xml)
                .querySelectorAll("parameter"))
                  .each(function (key, p) {
                  parameter_dict[p.id] = p.textContent;
                });
            }
          }

          if (URI(parameter_json_schema_url).protocol() === "") {
            // URL is relative, turn into absolute
            json_url_uri = URI(options.json_url);
            prefix = json_url_uri.path().split("/");
            prefix.pop();
            prefix = options.json_url.split(json_url_uri.path())[0] + prefix.join("/");
            parameter_json_schema_url = prefix + "/" + parameter_json_schema_url;
          }
          return g.renderParameterForm(parameter_json_schema_url, parameter_dict);
        })
        .push(function () {
          var i, div_list = g.props.element.querySelectorAll('.slapos-parameter-dict-key > div'),
            label_list = g.props.element.querySelectorAll('label.slapos-parameter-dict-key');

          console.log("Collapse paramaters");

          for (i = 0; i < div_list.length; i = i + 1) {
            $(div_list[i]).hide();
          }

          for (i = 0; i < label_list.length; i = i + 1) {
            $(label_list[i]).addClass("slapos-parameter-dict-key-colapse");
          }
          return g;
        })
        .push(function () {
          console.log("FINISHED TO RENDER, RETURNING THE GADGET");
          return g;
        })

        .fail(function (error) {
          var parameter_xml = '';
          console.log(error.stack);
          if (g.options.parameter.parameter_hash !== undefined) {
            parameter_xml = atob(g.options.parameter.parameter_hash);
          }
          return g.renderFailoverTextArea(parameter_xml, error.toString())
            .push(function () {
              error = undefined;
              return g;
            });
        });
    })
    .declareService(function () {
      var g = this,
        element = g.props.element.getElementsByTagName('select')[0];

      if (element === undefined) {
        return true;
      }

      function updateParameterForm(evt) {
        var e = g.props.element.getElementsByTagName('select')[0],
          parameter_shared = g.props.element.querySelector('input.parameter_shared');

        if (e === undefined) {
          throw new Error("Select not found.");
        }

        g.options.parameter.softwaretype = e.value;
        g.options.parameter.softwaretypeindex = e.selectedOptions[0]["data-id"];
        parameter_shared.value = e.selectedOptions[0]["data-shared"];
        return g.render(g.options)
          .push(function () {
            return loadEventList(g);
          });
      }

      return loopEventListener(
        element,
        'change',
        false,
        updateParameterForm.bind(g)
      );
    })
    .declareService(function () {
      var g = this,
        element = g.props.element.querySelector("button.slapos-show-raw-parameter");

      if (element === undefined) {
        return true;
      }

      function showRawParameter(evt) {
        var e = g.props.element.querySelector("button.slapos-show-raw-parameter"),
          to_show = g.props.element.querySelector("button.slapos-show-form"),
          parameter_xml;

        if (g.options.parameter.parameter_hash !== undefined) {
          parameter_xml = atob(g.options.parameter.parameter_hash);
        }

        $(e).addClass("hidden-button");
        $(to_show).removeClass("hidden-button");

        return g.renderRawParameterTextArea(parameter_xml)
          .push(function () {
            return loadEventList(g);
          });
      }

      return loopEventListener(
        element,
        'click',
        false,
        showRawParameter.bind(g)
      );
    })
    .declareService(function () {
      var g = this,
        element = g.props.element.querySelector("button.slapos-show-form");

      function showParameterForm(evt) {
        var e = g.props.element.getElementsByTagName('select')[0],
          to_hide = g.props.element.querySelector("button.slapos-show-form"),
          to_show = g.props.element.querySelector("button.slapos-show-raw-parameter");

        if (e === undefined) {
          throw new Error("Select not found.");
        }


        $(to_hide).addClass("hidden-button");
        $(to_show).removeClass("hidden-button");

        g.options.parameter.softwaretype = e.value;
        g.options.parameter.softwaretypeindex = e.selectedOptions[0]["data-id"];
        return g.render(g.options)
          .push(function () {
            return loadEventList(g);
          });
      }


      return loopEventListener(
        element,
        'click',
        false,
        showParameterForm.bind(g)
      );
    })
    .declareService(function () {
      return loadEventList(this);
    })
    .declareService(function () {
      var g = this;
      return g.processValidation(g.options.json_url)
        .fail(function (error) {
          var parameter_xml = '';
          console.log(error.stack);
          if (g.options.parameter.parameter_hash !== undefined) {
            parameter_xml = atob(g.options.parameter.parameter_hash);
          }
          return g.renderFailoverTextArea(parameter_xml, error.toString())
            .push(function () {
              error = undefined;
              return g;
            });
        });
    });

}(window, document, rJS, $, XMLSerializer, jQuery, vkbeautify));