tool = context.getPortalObject().portal_slapos_rest_api
return """
<ul id="vifib_monitoring"></ul>

<script>
$(document).ready(function () {
  $("ul#vifib_monitoring")
    .vifibmonitoring("fill_list", "%s");
});
</script>
""" % tool.absolute_url()
