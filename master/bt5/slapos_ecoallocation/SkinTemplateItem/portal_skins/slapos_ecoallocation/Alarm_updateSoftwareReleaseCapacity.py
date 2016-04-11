"""
  For all software releases, upgrade the Average CPU and Memory Capacity
"""

portal = context.getPortalObject()

portal.portal_catalog.searchAndActivate(
  portal_type="Software Release",
  method_id="SotftwareRelease_updateCapacityQuantity",
)
