from DateTime import DateTime

if start_date is None:
  start_date = ">=%s" % (DateTime()-45).strftime("%Y/%m/%d")

return len(context.portal_catalog(portal_type="Payment Transaction", 
                                  group_by="delivery.destination_section_uid", 
                                  simulation_state=["stopped", "delivered"],
                                  start_date=">=2017/05/01" ))
