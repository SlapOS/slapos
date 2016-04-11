return """
<div id="vifib_swipe"></div>

<div id="ad_content" class="hidden_fieldset">

<section>
Your instance will be available in some minutes, thank you for your patience. <br/>
</section>

<section>
We will not charge you when you configure your instance. Your first day of use is offered for free.<br/>
</section>

</div>

<script>
"use strict";
(function (window, $) {

  var current_slide = -1,
    content_id,
    methods;

  methods = {
    init: function (content_id) {
      if (content_id === undefined) {
        return $(this).removeAttr("data-slide").removeAttr("data-slide-id");
      } else {
        return $(this).attr("data-slide", -1).attr("data-slide-id", content_id);
      }
    },
    slide: function(timeout) {
      var context = $(this);
      context.rawslider("next");
      setTimeout(function () {
        context.rawslider("slide", timeout);
      }, timeout);
      return context;
    },
    next: function () {
      var content_id = $(this).attr("data-slide-id"),
        page,
        new_content = "",
        context = $(this);
      if (content_id === undefined) {
        // no initialized. return context to not break the chain
        return context;
      } else {
        page = parseInt(context.attr("data-slide"), 10) + 1;
        new_content = $("#" + content_id).find("section").eq(page).html();
        if (new_content === null) {
          page = 0;
          new_content = $("#" + content_id).find("section").eq(page).html();
        }
        if (new_content === null) {
          page = -1;
          new_content = "";
        }
        context.attr("data-slide", page);
        return context.html(new_content);
      }

    },
  };

  $.fn.rawslider = function (method) {
    var result;
    if (methods.hasOwnProperty(method)) {
      result = methods[method].apply(
        this,
        Array.prototype.slice.call(arguments, 1)
      );
    } else {
      $.error('Method ' + method +
              ' does not exist on jQuery.rawslider');
    }
    return result;
  };
}(window, jQuery));

$("#vifib_swipe")
  .css({
    "background-color": "black",
    "color": "#CCF",
    "font-size": "3em",
    "min-width": "100%",
    "min-height": "5em",
  })
  .rawslider("init", "ad_content")
  .rawslider("slide", 5000);
</script>
"""
