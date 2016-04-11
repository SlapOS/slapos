#
#  This method is used by the invoice_transaction_builder
# delivery builder to select the Invoice Transaction 
# in which creating new Invoice Transaction Lines.
#

deliveries_keys = {}
for movement in movement_list:
  ar = movement.getParentValue()
  line = None

  # case of tax movement  
  if ar.getSpecialiseValue().getPortalType() in ('Tax Rule', 'Tax Simulation Rule'):
    for other_rule in ar.getParentValue().contentValues():
      if other_rule == ar:
        continue
      for sm in other_rule.contentValues():
        line = sm.getDeliveryValue()

  # case of trade model movement
  if ar.getParentValue().getParentValue().getSpecialiseValue().getPortalType() in ('Trade Model Rule', 'Trade Model Simulation Rule'):
    line = ar.getParentValue().getParentValue().getParentValue().getDeliveryValue()

  # in case of invoice rule (ie. starting from Invoice)
  if line is None:
    line = ar.getParentValue().getOrderValue()

  # in case of invoicing rule (ie. starting from Order)
  if line is None:
    line = movement.getParentValue().getParentValue().getDeliveryValue()

  if line is not None:
    deliveries_keys[line.getExplanationValue()] = 1

return filter(lambda x : x is not None, deliveries_keys.keys())
