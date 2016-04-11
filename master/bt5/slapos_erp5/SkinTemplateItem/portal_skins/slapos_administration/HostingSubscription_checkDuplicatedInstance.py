from Products.CMFActivity.ActiveResult import ActiveResult
portal = context.getPortalObject()

software_instance_list = context.getSpecialiseRelatedValueList(
  portal_type=["Slave Instance", "Software Instance"])

if len(software_instance_list) == 1:
  return 

title_dict = {}

active_process = portal.restrictedTraverse(active_process)

for software_instance in software_instance_list:
  if software_instance.getSlapState() == "destroy_requested":
    continue

  title = software_instance.getTitle() 
  if title in title_dict:
    title_dict[title].append(software_instance.getObject())
  else:
    title_dict[title] = [software_instance.getObject()]


for title in title_dict:
  if len(title_dict[title]) > 1:
    if fixit:
      for software_instance in title_dict[title]:
        if len(software_instance.getAggregate([])) == 0:
          active_process.postResult(ActiveResult(
            summary="Fixing %s which duplication and is not allocated (%s)" \
                % (software_instance.getRelativeUrl(), context.getRelativeUrl()),
            severity=0,
            detail=""))
          software_instance.activate().SoftwareInstance_destroyAsSelf()          
    else:
      active_process.postResult(ActiveResult(
         summary="%s has duplication" % context.getRelativeUrl(),
         severity=100,
         detail="%s has duplication on %s (%s)" % (context.getRelativeUrl(), title, len(title_dict[title]))))
