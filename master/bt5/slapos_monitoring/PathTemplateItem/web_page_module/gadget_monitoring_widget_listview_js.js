/*global window, rJS, RSVP, Handlebars, loopEventListener, $ */
/*jslint nomen: true, indent: 2 */
(function (window, rJS, RSVP, Handlebars, loopEventListener, $) {
  "use strict";

  /////////////////////////////////////////////////////////////////
  // templates
  /////////////////////////////////////////////////////////////////
  var gadget_klass = rJS(window),
    templater = gadget_klass.__template_element,

    listbox_widget_table = Handlebars.compile(
      templater.getElementById("promise-widget-listbox").innerHTML
    ),
    listbox_header_widget = Handlebars.compile(
      templater.getElementById("header-widget-listbox").innerHTML
    );
  /*Handlebars.registerPartial(
    "listbox-widget-table-partial",
    templater.getElementById("listbox-widget-table-partial").innerHTML
  );*/

  /////////////////////////////////////////////////////////////////
  // some methods
  /////////////////////////////////////////////////////////////////
  function bindOnClick(element) {
    var fieldset = $(element.parentNode.querySelector('.ui-collapse-content')),
        line = $(element);
    if (line.hasClass('ui-icon-plus')) {
      line.removeClass('ui-icon-plus');
      line.addClass('ui-icon-minus');
    } else {
      line.removeClass('ui-icon-minus');
      line.addClass('ui-icon-plus');
    }
    if (fieldset !== undefined) {
      fieldset.toggleClass('ui-content-hidden');
    }
    return false;
  }

  gadget_klass

    /////////////////////////////////////////////////////////////////
    // ready
    /////////////////////////////////////////////////////////////////
    .ready(function (gadget) {
      gadget.property_dict = {
        render_deferred: RSVP.defer()
      };
    })

    .ready(function (gadget) {
      return gadget.getElement()
        .push(function (element) {
          gadget.property_dict.element = element;
          gadget.property_dict.block_index = 0;
          gadget.property_dict.filter_panel = $(gadget.property_dict.element.querySelector(".listbox-filter-panel"));
        });
    })
    .ready(function (gadget) {
      return gadget.getDeclaredGadget("jio_gadget")
        .push(function (jio_gadget) {
          gadget.property_dict.jio_gadget = jio_gadget;
        });
    })
    .ready(function (gadget) {
      gadget.property_dict.filter_panel.panel({
        "position-fixed": true,
        "display": "overlay",
        "position": "right",
        "theme": "b"
      });
    })
    .ready(function (gadget) {
      return gadget.property_dict.filter_panel.trigger("create");
    })

    /////////////////////////////////////////////////////////////////
    // published methods
    /////////////////////////////////////////////////////////////////

    /////////////////////////////////////////////////////////////////
    // acquired methods
    /////////////////////////////////////////////////////////////////
    .declareAcquiredMethod("jio_get", "jio_get")
    .declareAcquiredMethod("jio_allDocs", "jio_allDocs")
    .declareAcquiredMethod("getUrlFor", "getUrlFor")
    .declareAcquiredMethod("translate", "translate")
    .declareAcquiredMethod("redirect", "redirect")

    /////////////////////////////////////////////////////////////////
    // declared methods
    /////////////////////////////////////////////////////////////////
    .declareMethod('render', function (option_dict) {
      var gadget = this,
        content = '',
        k,
        k_len,
        search_string = '',
        translated_column_list = [],
        all_document_list = [],
        all_docs_result,
        render_listview,
        render_bloc_list = [
          ".custom-listbox .ui-block-a",
          ".custom-listbox .ui-block-b"];
          //".custom-listbox .ui-block-c"];

      // Create the search query
      if (option_dict.search) {
        search_string = '(' + option_dict.column.select + ':"%' + option_dict.search + '%"' + ')';
        for (k = 0, k_len = option_dict.collapsed_list.length; k < k_len; k += 1) {
          search_string  += ' OR (' + option_dict.collapsed_list[k].select +
            ':"%' + option_dict.search + '%"' + ')';
        }
        option_dict.query.query = search_string + ' AND ' + option_dict.query.query;
      }

      render_listview = function () {
        var jio_options,
          render_promise = [];
        if (option_dict.data_url !== undefined && option_dict.data_url !== '') {
          jio_options = {
            type: "query",
            sub_storage: {
              type: "drivetojiomapping",
              sub_storage: {
                type: "dav",
                url: option_dict.data_url
              }
            }
          };
          gadget.property_dict.jio_gadget.createJio(jio_options);
          render_promise.push(
              gadget.property_dict.jio_gadget.allDocs(option_dict.query));
        } else {
          render_promise.push(gadget.jio_allDocs(option_dict.query));
        }
        return new RSVP.Queue()
          .push(function () {
            return RSVP.all(render_promise);
          });
      };

      // store initial configuration
      gadget.property_dict.option_dict = option_dict;

      return render_listview()
        .push(function (result_list) {
        var promise_list = [],
          i_len,
          i,
          result = result_list[0];
        all_docs_result = result_list[0];
        for (i = 0, i_len = result.data.total_rows; i < i_len; i += 1) {
          promise_list.push(gadget.getUrlFor({
            jio_key: result.data.rows[i].id,
            jio_for: option_dict.data_url || '',
            page: 'view'
          }));
        }
  
        return RSVP.all(promise_list);
      })
      .push(function (link_list) {
        var row_list = [],
          cell_list,
          datarow_list = all_docs_result.data.rows,
          i_len,
          i,
          j_len,
          j;
  
        // build handlebars object
  
        for (j = 0, j_len = all_docs_result.data.total_rows; j < j_len; j += 1) {
          var data_list=[];
          for (i = 0; i < option_dict.collapsed_list.length; i += 1) {
            data_list.push({
              "icon_class": option_dict.collapsed_list[i].icon_class,
              "text_value": datarow_list[j].value.hasOwnProperty(option_dict.collapsed_list[i].select) ? datarow_list[j].value[option_dict.collapsed_list[i].select]: '',
              "inline": option_dict.collapsed_list[i].inline,
              "class": option_dict.collapsed_list[i].css_class
            });
          }
          row_list.push({
            "href": link_list[j],
            "value": datarow_list[j].value[option_dict.column.select],
            "status": datarow_list[j].value.hasOwnProperty('status') ? datarow_list[j].value.status.toLowerCase() : '',
            "data_list": data_list
          });
        }
  
        /*for (i = 0; i < option_dict.column_list.length; i += 1) {
          translated_column_list.push(gadget.translate(option_dict.column_list[i].title));
        }*/
        return RSVP.all([
          row_list
        ]);
      })
      .push(function (result_list) {
        var header_content = '',
          render_header = option_dict.render_header || true,
          index = gadget.property_dict.block_index % 2,
          sort_element;
        if (render_header) {
          header_content += listbox_header_widget({
            widget_theme : option_dict.widget_theme,
            search: option_dict.search
          });
          gadget.property_dict.element.querySelector(".center")
            .innerHTML = header_content;
          if (option_dict.query.sort_on && option_dict.query.sort_on[0]) {
            sort_element = gadget.property_dict.element.querySelector('#listview-sort-' + option_dict.query.sort_on[0][0]);
            if (sort_element) {
              sort_element.checked = true;
            }
          }
          
        }
        if (result_list[0].length > 0) {
          content += listbox_widget_table({
            row_list: result_list[0],
            header: option_dict.header || {}
          });
          gadget.property_dict.element.querySelector(render_bloc_list[index])
            .innerHTML += content;
        }
        gadget.property_dict.render_deferred.resolve();
      })
      .push(function () {
        gadget.property_dict.block_index += 1;
      });
    })

    /////////////////////////////////////////////////////////////////
    // declared service
    /////////////////////////////////////////////////////////////////
    .declareService(function () {
      var gadget = this;
      return new RSVP.Queue()
        .push(function () {
          return gadget.property_dict.render_deferred.promise;
        })
        .push(function () {
          var promise_list = [],
            element_list = gadget.property_dict.element.querySelectorAll('.ui-listview li > a'),
            i;
          for (i = 0; i < element_list.length; i += 1) {
            promise_list.push(loopEventListener(
              element_list[i],
              'click',
              false,
              bindOnClick.bind(gadget, element_list[i])
            ));
          }
          promise_list.push($(".ui-field-contain input[type='radio']").change(function () {
            var sort_on = 'status';
            if (!$("#listview-sort-status").is(':checked')) {
              sort_on = 'title';
            }
            return gadget.redirect({
              page: gadget.property_dict.option_dict.search_page || '',
              search: gadget.property_dict.option_dict.search || '',
              sort_on: sort_on
            });
          }));
          /*element_list = gadget.property_dict.element.querySelectorAll(".ui-field-contain input[type='radio']");
          for (i = 0; i < element_list.length; i += 1) {
            promise_list.push(
              loopEventListener(
              element_list[i],
              'change',
              true,
              bindRadioClick.bind(gadget, element_list[i])
            ));
          }*/
          promise_list.push(loopEventListener(
            gadget.property_dict.element.querySelector('form.search'),
            'submit',
            false,
            function (evt) {
              return gadget.redirect({
                jio_key: gadget.property_dict.option_dict.jio_key || '',
                page: gadget.property_dict.option_dict.search_page || '',
                sort_on: gadget.property_dict.option_dict.sort_on || '',
                search: evt.target[0].value
              });
            })
          );
          promise_list.push(loopEventListener(
            gadget.property_dict.element.querySelector('.listview-refresh'),
            'click',
            false,
            function (evt) {
              return gadget.redirect({
                page: gadget.property_dict.option_dict.search_page || '',
                sort_on: gadget.property_dict.option_dict.sort_on || '',
                search: gadget.property_dict.option_dict.search || '',
                t: Date.now() / 1000 | 0
              });
            })
          );
          promise_list.push(loopEventListener(
            gadget.property_dict.element.querySelector('.listview-filter'),
            'click',
            false,
            function (evt) {
              gadget.property_dict.filter_panel.panel("toggle");
            })
          );
          promise_list.push(loopEventListener(
            gadget.property_dict.element.querySelector('form.filter'),
            'submit',
            false,
            function (evt) {
              var filter_status = [],
                element = gadget.property_dict.element;
              if (element.querySelector('#monitor-promise-error').checked) {
                filter_status.push('error');
              }
              if (element.querySelector('#monitor-promise-success').checked) {
                filter_status.push('ok');
              }
              if (element.querySelector('#monitor-promise-warning').checked) {
                filter_status.push('warning');
              }
              return gadget.redirect({
                page: gadget.property_dict.option_dict.search_page || '',
                sort_on: gadget.property_dict.option_dict.sort_on || '',
                search: gadget.property_dict.option_dict.search || '',
                status: filter_status.join('+')
              });
            })
          );
          return RSVP.all(promise_list);
        });
    });

}(window, rJS, RSVP, Handlebars, loopEventListener, $));
