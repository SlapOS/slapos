computer = state_change['object']
portal = computer.getPortalObject()
person = portal.ERP5Site_getAuthenticatedMemberPersonValue()
computer.edit(
  allocation_scope='open/personal',
  source_administration_value=person,
)
portal.portal_workflow.doActionFor(computer, 'validate_action')
