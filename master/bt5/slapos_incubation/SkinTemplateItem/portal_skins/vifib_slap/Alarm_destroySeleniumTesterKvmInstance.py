from Products.ZSQLCatalog.SQLCatalog import NegatedQuery, Query

portal = context.getPortalObject()
person = portal.restrictedTraverse('person_module/20120411-A56ED', None)
if person is None:
  return
person_reference = person.getReference()

setup_service = portal.restrictedTraverse(portal.portal_preferences.getPreferredInstanceSetupResource())

# XXX Owner column should not be used to fetch the list!
# Data model of hosting subscription should be fixed to allow direct query
portal.portal_catalog.searchAndActivate(
  portal_type="Hosting Subscription",
  owner=person_reference,
  validation_state="validated",
  method_id='HostingSubcription_requestDestructionSeleniumTester',
  method_kw={'tag': tag},
  activate_kw={'tag': tag},
)

context.activate(after_tag=tag).getId()
