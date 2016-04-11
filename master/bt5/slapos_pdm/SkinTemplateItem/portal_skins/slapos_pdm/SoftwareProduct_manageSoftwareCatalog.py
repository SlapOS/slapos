portal = context.getPortalObject()

software_release_url = None

for software_release in portal.portal_catalog(
    portal_type='Software Release',
    validation_state='published',
    default_aggregate_uid=context.getUid(),
    sort_on=(('indexation_timestamp', 'DESC'),)):
  installed_count = portal.portal_catalog(
    software_release_url=software_release.getUrlString(),
    allocation_scope_uid=portal.portal_categories.allocation_scope.open.public.getUid(),
    capacity_scope_uid=portal.portal_categories.capacity_scope.open.getUid(),
    portal_type='Computer Partition',
    free_for_request=1,
    limit=1,
  )
  if len(installed_count) > 0:
    software_release_url = software_release.getRelativeUrl()
    break

if context.getAggregate() != software_release_url:
  context.setAggregate(software_release_url)
