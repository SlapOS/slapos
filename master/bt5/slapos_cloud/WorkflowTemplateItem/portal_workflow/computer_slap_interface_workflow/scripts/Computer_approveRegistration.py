computer = state_change['object']
portal = computer.getPortalObject()
person = portal.ERP5Site_getAuthenticatedMemberPersonValue()
computer.edit(
  allocation_scope='open/personal',
  source_administration_value=person,
)

erp5_login = computer.newContent(
  portal_type="ERP5 Login",
  reference=computer.getReference()
)
erp5_login.validate()

portal.portal_workflow.doActionFor(computer, 'validate_action')
