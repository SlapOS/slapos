"""
  When the workflow history is too big the response time
  of getCreationDate is too high.

  Use Cache to void recalculate it.
"""
from Products.ERP5Type.Cache import CachingMethod

portal = context.getPortalObject()

def getCachedCreationDate(relative_url):
  return portal.restrictedTraverse(relative_url).getCreationDate()

return CachingMethod(getCachedCreationDate,
                     id="Base_getCachedCreationDate_",
                     cache_factory="dms_cache_factory")(context.getRelativeUrl())
