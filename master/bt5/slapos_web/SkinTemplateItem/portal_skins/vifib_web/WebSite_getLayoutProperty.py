"""Return a property layout from a website.
Useful to use notification message reference from website configuration not in website context."""
portal = context.getPortalObject()
current_web_site = portal.getWebSiteValue()
try:
  website = getattr(portal.web_site_module,website)
except TypeError:
  #website parameter is None
  website = current_website
except AttributeError:
  #website parameter is from a non existant web site
  website = current_web_site

return website.getLayoutProperty(reference, defaultValue)
