portal = context.getPortalObject()
portal.portal_catalog.searchAndActivate(
      portal_type="Regularisation Request", 
      simulation_state=["suspended"],
      method_id='RegularisationRequest_cancelInvoiceIfPersonOpenOrderIsEmpty',
      activate_kw={'tag': tag}
      )
context.activate(after_tag=tag).getId()
