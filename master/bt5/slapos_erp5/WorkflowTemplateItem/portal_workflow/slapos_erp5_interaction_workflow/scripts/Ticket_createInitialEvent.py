# Added this script to be running as Owner
portal = context.getPortalObject()

return portal.event_module.newContent(
  portal_type="Web Message",
)
