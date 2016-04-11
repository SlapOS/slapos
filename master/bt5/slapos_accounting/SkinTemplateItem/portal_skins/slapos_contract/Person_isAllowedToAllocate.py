portal = context.getPortalObject()
person = context
contract_portal_type = "Cloud Contract"

contract = portal.portal_catalog.getResultValue(
  portal_type=contract_portal_type,
  default_destination_section_uid=person.getUid(),
  validation_state='validated',
)

if (contract is not None) and (contract.getValidationState() == "validated"):
  return True
else:
  return False
