return """
<script>
"use strict";
(function ($) {

  var methods;

  methods = {
    click: function (method) {
      $(this).click(function() {
        $(this).parent().parent()
          .slapostoken(method);
        return false;
      });
    },
    generateComputerToken: function () {
      $.ajax("./Base_generateComputerTokenFromJS", {
        context: $(this),
        success: function(data) {
          $(this).attr("class", "alignr")
                 .text("New token: " + data.access_token);
        }
      })
    },
    generateCredentialToken: function () {
      $.ajax("./Base_generateCredentialTokenFromJS", {
        context: $(this),
        success: function(data) {
          $(this).attr("class", "alignr")
                 .text("New token: " + data.access_token);
        }
      })
    },
    generateRssRestrictedAccessToken: function () {
      $.ajax("./Base_generateRssRestrictedAccessTokenFromJS", {
        context: $(this),
        success: function(data) {
          $(this).html("<a target='_blank' href='" + data.restricted_access_url +
              "'>Your RSS Feed link</a>");
        }
      })
    },
  };

  $.fn.slapostoken = function (method) {
    var result;
    if (methods.hasOwnProperty(method)) {
      result = methods[method].apply(
        this,
        Array.prototype.slice.call(arguments, 1)
      );
    } else {
      $.error('Method ' + method +
              ' does not exist on jQuery.slapostoken');
    }
    return result;
  };
}(jQuery));

$("#computertokengenerationlink")
  .slapostoken("click", "generateComputerToken");
$("#credentialtokengenerationlink")
  .slapostoken("click", "generateCredentialToken");
$("#rssaccesstokengenerationlink")
  .slapostoken("click", "generateRssRestrictedAccessToken");
</script>
"""
