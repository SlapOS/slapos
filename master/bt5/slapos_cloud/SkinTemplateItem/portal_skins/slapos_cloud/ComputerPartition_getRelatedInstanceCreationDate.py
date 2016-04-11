from DateTime import DateTime

partition = context

software_instance = partition.getAggregateRelatedValueList(portal_type=["Software Instance", "Slave Instance"])[0].getObject()
date = DateTime(software_instance.getCreationDate())
return date.strftime('%Y/%m/%d %H:%M')
