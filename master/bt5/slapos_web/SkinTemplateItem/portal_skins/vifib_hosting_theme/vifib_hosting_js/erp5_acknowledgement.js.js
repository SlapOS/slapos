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

  var notificationload,
    notificationdisplay,
    notificationsettimeout,
    notificationhide,
    notificationdismiss,
    methods;

  notificationload = function (context) {
    $.ajax({
      url: 'AcknowledgementTool_getUserUnreadAcknowledgementJSON',
      dataType: 'json',
      context: context,
      success: function (data) {
        notificationhide($(this));
        var result = data.result;
        if (result.length === 0) {
          notificationsettimeout($(this));
        } else {
          notificationdisplay($(this), data.result[0]);
        }
      },
      error: function () {
        notificationsettimeout($(this));
      }
    });
  };

  notificationdisplay = function (context, acknowledgement_json) {
    context
      .css({
        "width": "300px",
        "min-height": "5em",
        "z-index": "9999",
        "position": "fixed",
        "top": "1em",
        "left": "1em",
        "text-align": "center",
        "color": "#eee",
        "font-weight": "bold",
        "font-size": "14px",
        "text-shadow": "1px 1px 0 #000",
        "background-color": "#59bae2",
        "padding": "2px 11px 8px 11px",
        "border-radius": "15px"
      })
      .show()
      .html(acknowledgement_json.text_content)
      .append("<br/><br/><button id='acknowledgement_button'>Mark as read</button>")
      .find("#acknowledgement_button")
      .attr("data-acknowledgement-url", encodeURIComponent(acknowledgement_json.acknowledge_url))
      .click(function () {
        var url = decodeURIComponent($(this).attr("data-acknowledgement-url"));
        notificationdismiss($(this).parent(), url);
        return false;

      })
      ;
  };

  notificationhide = function (context) {
    context.hide();
  };

  notificationdismiss = function (context, url) {
    notificationhide(context);
    $.ajax({
      type: 'POST',
      url: url,
      context: context,
      async: true,
      complete: function () {
        notificationload($(this));
      }
    });
  };

  notificationsettimeout = function (context) {
    setTimeout(function () {
      notificationload(context);
    }, 600000);
  };

  methods = {
    init: function () {
      notificationload($(this));
      return $(this);
    },
  };

  $.fn.slaposnotification = function (method) {
    var result;
    if (methods.hasOwnProperty(method)) {
      result = methods[method].apply(
        this,
        Array.prototype.slice.call(arguments, 1)
      );
    } else {
      $.error('Method ' + method +
              ' does not exist on jQuery.slaposnotification');
    }
    return result;
  };
}(window, jQuery));

$(document).ready(function () {
  $("#acknowledgement_zone").slaposnotification("init");
});

