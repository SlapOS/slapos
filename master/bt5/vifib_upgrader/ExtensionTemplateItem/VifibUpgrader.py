from Products.ERP5Type.Base import WorkflowMethod

@WorkflowMethod.disable
def DeliveryLineSetZeroPriceAndOrUpdateAppliedRule(self):
  portal_type = self.getPortalType()
  assert( portal_type in self.getPortalDeliveryMovementTypeList())
  common_specialise = 'sale_trade_condition_module/vifib_trade_condition'
  specialise = self.getParentValue().getSpecialise()
  if common_specialise != specialise:
    self.getParentValue().setSpecialise(common_specialise)
  self.getParentValue().SalePackingList_setArrow()
  self.setPrice(0.0)
  if self.getSimulationState() == 'cancelled':
    # force no simulation
    self.setQuantity(0.0)
  else:
    self.setQuantity(1.0)
    self.Delivery_updateAppliedRule()

from DateTime import DateTime
@WorkflowMethod.disable
def OpenSaleOrderLine_migrate(self):
  now = DateTime().earliestTime()
  self.setStartDate(now)
  self.setStopDate(now)
  self.setPrice(0.0)
  self.setQuantity(1.0)
  self.setResource(self.getPortalObject().portal_preferences.getPreferredInstanceSubscriptionResource())
  resource_value = self.getResourceValue()
  self.setBaseContributionList(resource_value.getBaseContributionList())
  self.setUseList(resource_value.getUseList())
  self.setQuantityUnit(resource_value.getQuantityUnit())
  self.setSpecialise('sale_trade_condition_module/vifib_trade_condition')
  self.setSourceSection('organisation_module/vifib_internet')
  self.setSource('organisation_module/vifib_internet')
  self.setDestination(self.getParentValue().getDestinationSection())
  self.setDestinationSection(self.getParentValue().getDestinationSection())
  self.setPriceCurrency('currency_module/EUR')
