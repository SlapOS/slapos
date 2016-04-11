"""Get the release of the selected product"""
portal = context.getPortalObject()
session = context.WebSection_getVifibSession()
params = portal.portal_selections.getSelectionParamsFor('vifib_session_id')
uid = params['instance_software_product_uid']

# assert there is only one item
if uid is None:
  raise AttributeError, "There should be only one selected software product"
else:
  return context.portal_catalog(
    portal_type="Software Release",
    default_aggregate_uid=uid,
    validation_state=["shared", "shared_alive", "released", "released_alive", "published", "published_alive"]
    )
