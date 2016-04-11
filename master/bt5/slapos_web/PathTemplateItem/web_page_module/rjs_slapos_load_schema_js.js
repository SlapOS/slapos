/*jslint nomen: true, maxlen: 200, indent: 2*/
/*global window, rJS, console, RSVP, jQuery, jIO, tv4, URI, JSON, $ */
(function (window, rJS, $, RSVP) {
  "use strict";

  var gk = rJS(window);

  function getJSON(url) {
    var protocol = URI(url).protocol(); 
    if ( protocol === "http" || protocol === "https" ) { 
      if (URI(window.location).protocol() !==  protocol) {
        throw new Error("You cannot mixed http and https calls");
      }
    }
    return RSVP.Queue()
      .push(function () { 
        return jIO.util.ajax({
          url: url
        })
        .then(function (evt) {
          return evt.target.responseText;
        });
      });
  }

  function resolveLocalReference(ref, schema) {
    // 2 here is for #/
    var i, ref_path = ref.substr(2, ref.length),
      parts = ref_path.split("/");
    if (parts.length === 1 && parts[0] === "") {
      // It was uses #/ to reference the entire json so just return it.
      return schema;
    }
    for (i = 0; i < parts.length; i += 1) {
      schema = schema[parts[i]];
    }
    return schema;
  }

  function resolveReference(partial_schema, schema, base_url) {
    var parts,
      external_schema,
      ref = partial_schema.$ref;

    if (ref === undefined) {
      return RSVP.Queue().push(function () {
        return partial_schema;
      });
    }

    if (ref.substr(0, 1) === "#") {
      return RSVP.Queue().push(function () {
        return resolveLocalReference(ref, schema);
      });
    }

    return RSVP.Queue().push(function () {
      if (URI(ref).protocol() === "") {
        if (base_url !== undefined) {
          ref = base_url + "/" + ref;
        }
      }
      return getJSON(ref);
    })
      .push(function (json) {
        external_schema = JSON.parse(json);
        parts = ref.split("#");
        ref = "#" + parts[1];
        return resolveLocalReference(ref, external_schema);
      });
  }

  function clone(obj) {
    return JSON.parse(JSON.stringify(obj));
  }

  // Inspired from https://github.com/nexedi/dream/blob/master/dream/platform/src/jsplumb/jsplumb.js#L398
  function expandSchema(json_schema, full_schema, base_url) {
    var i,
      expanded_json_schema = clone(json_schema) || {};

    if (!expanded_json_schema.properties) {
      expanded_json_schema.properties = {};
    }

    return RSVP.Queue().push(function () {
      if (json_schema.$ref) {
        return resolveReference(
          json_schema,
          full_schema,
          base_url
        )
          .push(function (remote_schema) {
            return expandSchema(
              remote_schema,
              full_schema,
              base_url
            );
          }).push(function (referencedx) {
            $.extend(expanded_json_schema, referencedx);
            delete expanded_json_schema.$ref;
            return true;
          });
      }
      return true;
    }).push(function () {

      var property, queue = RSVP.Queue();

      function wrapperResolveReference(p) {
        return resolveReference(
          json_schema.properties[p],
          full_schema,
          base_url
        ).push(function (external_schema) {
          // console.log(p);
          return expandSchema(
            external_schema,
            full_schema,
            base_url
          )
            .push(function (referencedx) {
              $.extend(expanded_json_schema.properties[p], referencedx);
              if (json_schema.properties[p].$ref) {
                delete expanded_json_schema.properties[p].$ref;
              }
              return referencedx;
            });
        });
      }

      // expand ref in properties
      for (property in json_schema.properties) {
        if (json_schema.properties.hasOwnProperty(property)) {
          queue.push(
            wrapperResolveReference.bind(this, property)
          );
        }
      }
      return queue;
    })
      .push(function () {

        var zqueue = RSVP.Queue();

        function wrapperExpandSchema(p) {
          return expandSchema(
            json_schema.allOf[p],
            full_schema,
            base_url
          ).push(function (referencedx) {
            if (referencedx.properties) {
              $.extend(
                expanded_json_schema.properties,
                referencedx.properties
              );
              delete referencedx.properties;
            }
            $.extend(expanded_json_schema, referencedx);
          });
        }

        if (json_schema.allOf) {
          for (i = 0; i < json_schema.allOf.length; i += 1) {
            zqueue.push(wrapperExpandSchema.bind(this, i));
          }
        }
        return zqueue;
      })
      .push(function () {
        if (expanded_json_schema.allOf) {
          delete expanded_json_schema.allOf;
        }
        if (expanded_json_schema.$ref) {
          delete expanded_json_schema.$ref;
        }
        // console.log(expanded_json_schema);
        return clone(expanded_json_schema);
      });
  }
  function getMetaJSONSchema() {
    return getJSON("../../renderjs/slapos_load_meta_schema.json");
  }

  function validateJSONSchema(json, base_url) {
    return getMetaJSONSchema()
      .push(function (meta_schema) {
        if (!tv4.validate(json, meta_schema)) {
          throw new Error("Non valid JSON schema " + json);
        }
        return JSON.parse(json);
      })
      .push(function (schema) {
        return expandSchema(schema, schema, base_url);
      });
  }

  gk
    .declareMethod("loadJSONSchema", function (url) {
      return getJSON(url)
        .push(function (json) {
          var base_url, url_uri;

          url_uri = URI(url);
          base_url = url_uri.path().split("/");
          base_url.pop();
          base_url = url.split(url_uri.path())[0] + base_url.join("/");
          
          return validateJSONSchema(json, base_url);
        });
    })

    .declareMethod("loadSoftwareJSON", function (url) {
      return getJSON(url)
        .push(function (json) {
          return JSON.parse(json);
        });
    })

    .declareMethod("validateJSONForSoftwareType", function (schema_url, software_type, generated_json) {
      return getJSON(schema_url)
        .push(function (json) {
          return JSON.parse(json);
        })
        .push(function (json_object) {
          var parameter_schema_url,
            st,
            base_url,
            url_uri = URI(schema_url);
        
          for (st in json_object["software-type"]) {
            if (json_object["software-type"].hasOwnProperty(st)) {
              if (st === software_type) {
                parameter_schema_url = json_object["software-type"][st].request;
              }
            }
          }
          
          if (URI(parameter_schema_url).protocol() === "") {
            base_url = url_uri.path().split("/");
            base_url.pop();
            base_url = schema_url.split(url_uri.path())[0] + base_url.join("/");
            if (base_url !== undefined) {
              parameter_schema_url = base_url + "/" + parameter_schema_url;
            }
          }
          
          return getJSON(parameter_schema_url)
            .push(function (json) {
              var schema = JSON.parse(json);

              return expandSchema(schema, schema, base_url)
                .push(function (loaded_json) {
                  return tv4.validateMultiple(generated_json, loaded_json);
                });
            });
         });
    })

    .declareMethod("validateJSON", function (schema_url, generated_json) {
      return getJSON(schema_url)
        .push(function (json) {
          var base_url,
            url_uri = URI(schema_url),
            schema = JSON.parse(json);

          base_url = url_uri.path().split("/");
          base_url.pop();
          base_url = schema_url.split(url_uri.path())[0] + base_url.join("/");

          return expandSchema(schema, schema, base_url)
            .push(function (loaded_schema) {
              return tv4.validateMultiple(generated_json, loaded_schema);
            });
        });
    });

}(window, rJS, $, RSVP));