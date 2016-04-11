tool = context.getPortalObject().portal_slapos_rest_api
return """
<script>
$(document).ready(function () {
  var context = $(".allocable_to_check"),
    checkallocable,
    timer,
    xhr,
    key, i,
    sla_key_list;

  sla_key_list = [
    'cpu_core',
    'cpu_frequency',
    'cpu_type',
    'local_area_network_type',
    'memory_size',
    'memory_type',
    'region',
    'storage_capacity',
    'storage_interface',
    'storage_redundancy',
    'computer_guid',
    'group',
    'network_guid',
  ];

  checkallocable = function () {
    var context = $(".allocable_to_check"),
      sla = {}, val;

    if (timer !== undefined) {
      clearTimeout(timer);
    }
    if (xhr !== undefined) {
      xhr.abort();
    }

    for (i=0; i<sla_key_list.length; i+=1) {
      key = sla_key_list[i];
      val = $('[name="field_your_' + key + '"]').val();
      if (val) {
        sla[key] = val;
      }
    }
    
    context.text("checking...");
    xhr = $.vifiballocable({
      context: context,
      url: '%s/v1/instance/request', 
      slave: false, 
      software_release: context.attr("data-url"), 
      software_type: "default", 
      sla: sla,
      success: function(data) {
        if (data.result === true) {
          $(this).text("There is space!");
        } else {
          $(this).text("Sorry, no space left in the cloud :(");
        }
      }, 
      error: function(data) {
        $(this).text("Unable to check if there is space");
      }, 
      complete: function () {
        timer = setTimeout(function() {
          checkallocable();
          }, 60000);
      },
    });
  };
  for (i=0; i<sla_key_list.length; i+=1) {
    key = sla_key_list[i];
    $('[name="field_your_' + key + '"]').change(checkallocable);
  }

  checkallocable();
});


</script>
""" % tool.absolute_url()
