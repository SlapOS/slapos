portal = context.getPortalObject()
return portal.absolute_url() + "/#/" + context.getRelativeUrl()
