portal = context.getPortalObject()

if context.getPortalType() == "Computer":

  # Get the Latest Sale Packing List
  sale_packing_list_line = portal.portal_catalog.getResultValue(
                        portal_type='Sale Packing List Line',
                        simulation_state='delivered',
                        sort_on=[('movement.start_date', 'DESC')],
                        aggregate_uid=context.getUid(),
                        limit=1)
  
  if sale_packing_list_line is not None:
    sale_packing_list = sale_packing_list_line.getParent()
  
    #request = context.getPortalObject().REQUEST
    return sale_packing_list.Base_redirect('Base_viewListMode?proxy_form_id=SalePackingList_view&proxy_field_id=listbox')

# Redirect to web site to hide the indexation process
context.Base_redirect('view', keep_items={'portal_status_message':context.Base_translateString('No Consumption Report for this computer.')})
