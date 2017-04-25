/*
Copyright (c) 2012 Nexedi SA and Contributors. All Rights Reserved.

This program is Free Software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
*/
"use strict";
(function (window, $) {

  var methods,
    Base61,
    update_status,
    search_document_list;

  // http://stackoverflow.com/a/246813
  Base61 = {
    // private property
    _keyStr : "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",
    // public method for encoding
    encode : function (input) {
        var output = "";
        var chr1, chr2, chr3, enc1, enc2, enc3, enc4;
        var i = 0;

    //     input = Base64._utf8_encode(input);

        while (i < input.length) {

            chr1 = input.charCodeAt(i++);
            chr2 = input.charCodeAt(i++);
            chr3 = input.charCodeAt(i++);

            enc1 = chr1 >> 2;
            enc2 = ((chr1 & 3) << 4) | (chr2 >> 4);
            enc3 = ((chr2 & 15) << 2) | (chr3 >> 6);
            enc4 = chr3 & 60;

            if (isNaN(chr2)) {
                enc3 = enc4 = 61;
            } else if (isNaN(chr3)) {
                enc4 = 61;
            }

            output = output +
            this._keyStr.charAt(enc1) + this._keyStr.charAt(enc2) +
            this._keyStr.charAt(enc3) + this._keyStr.charAt(enc4);

        }

        return output;
    }
  };


  update_status = function (context) {
    var status_url = decodeURIComponent(context.attr("data-url"));
    context.attr("class", "check_monitoring")
           .attr("title", "Checking status");
    $.ajax({
      type: 'GET',
      url: status_url,
      dataType: 'json',
      async: true,
      context: context, 
      success: function(data) {
        var created_at = new Date(Date.parse(data.created_at)),
          now = new Date(),
          context = $(this);
        // 5 minute for computer. 1 day for instance.
        if (/#access/.test(data.text) & /computer_module/.test(data['@document']) & (now - created_at < 300000)) {
          $(this).attr("class", "monitoring_ok")
                 .attr("title", data.text + " (" + created_at + ")" )
                 .attr("href", data['@document']);
        } else if (/#access/.test(data.text) & /software_instance_module/.test(data['@document']) & (now - created_at < 86400000)) {
          $(this).attr("class", "monitoring_ok")
                 .attr("title", data.text + " (" + created_at + ")" )
                 .attr("href", data['@document']);
        } else if (/#access/.test(data.text) & /software_installation_module/.test(data['@document']) & (now - created_at < 86400000)) {
          $(this).attr("class", "monitoring_ok")
                 .attr("title", data.text + " (" + created_at + ")" )
                 .attr("href", data['@document']);
        } else {
          $(this).attr("class", "monitoring_error")
                 .attr("title", data.text + " (" + created_at + ")" )
                 .attr("href", data['@document']);
        }
        setTimeout(function () {
          update_status(context);
        }, 60000);
      },
      error: function(jqXHR, textStatus, errorThrown) {
        // XXX Drop content instead
        // $(this).attr("class", "monitoring_failed");
        var context = $(this);
        if (jqXHR.status === 404) {
          context.remove()
        } else {
          $(this).attr("class", "monitoring_failed")
                 .attr("title", "Unable to fetch content");
          setTimeout(function () {
            update_status(context);
          }, 60000);
        }
      }
    });
  };

  search_document_list = function (context, list_url) {

    context.attr('data-list-url', list_url);
    $.ajax({
      type: 'GET',
      url: list_url,
      dataType: 'json',
      async: true,
      context: context, 
      success: function(data) {
        var result_list = data.list || [],
          i;

        for (i=0; i<result_list.length; i += 1) {
          var status_url = result_list[i],
            status_id,
            status_context;
          status_id = encodeURIComponent(Base61.encode(status_url)),
          status_context = $(this).find('#' + status_id);
          if (!status_context[0]) {
            status_context = $(this).append('<li><a class="check_monitoring" id="' + status_id + '" data-url="' + encodeURIComponent(status_url) + '"></a></li>')
                                    .find('#' + status_id);
            (function(new_context) {
              setTimeout(function () {
                update_status(new_context);
              });
            })(status_context);
          }
        }
      },
      complete: function() {
        var context = $(this);
        setTimeout(function () {
          search_document_list(context, context.attr('data-list-url'));
        }, 60000);
      }
    });
  };



  methods = {
    fill_list: function (base_url) {
      var context = $(this),
        list_url = base_url + "/v1/status/"; // XXX Hardcoded
      setTimeout(function () {
        search_document_list(context, list_url);
      });
      return context;
    },
    check_status: function (base_url, relative_path) {
      var context = $(this),
        status_url = base_url + "/v1/status/" + relative_path; // XXX Hardcoded
      context.attr("data-url", encodeURIComponent(status_url));
      setTimeout(function () {
        update_status(context);
      });
      return context;
    }
  };

  $.fn.vifibmonitoring = function (method) {
    var result;
    if (methods.hasOwnProperty(method)) {
      result = methods[method].apply(
        this,
        Array.prototype.slice.call(arguments, 1)
      );
    } else {
      $.error('Method ' + method +
              ' does not exist on jQuery.vifibmonitoring');
    }
    return result;
  };
}(window, jQuery));
