return """
<script>
"use strict";
$(document).ready(function(){

    $("#destroy_hs").click(function(){
        if ($(this).attr("rel") !== "confirm") {
          $(this).val("Confirm destruction");
          $(this).attr("rel", "confirm");
          $("#alert_destroy_hs").fadeIn(200);
          $("#alert_destroy_hs").css("display", "inline-block");
          return false;
        }
    });
    $("#alert_destroy_hs").click(function(){
       $("#destroy_hs").attr("rel", "");
       $("#destroy_hs").val("Destroy");
       $(this).fadeOut(500);
    });
});
</script>
"""
