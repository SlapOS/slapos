tool = context.getPortalObject().portal_slapos_rest_api
return """
<script>
$(document).ready(function () {
  $(".monitoring_to_check").each(function() {
    $(this).vifibmonitoring("check_status", "%s", $(this).attr("data-relative-url"));
  });
});
</script>
""" % tool.absolute_url()
