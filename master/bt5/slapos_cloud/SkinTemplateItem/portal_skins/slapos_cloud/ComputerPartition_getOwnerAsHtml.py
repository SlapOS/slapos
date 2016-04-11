partition = context

si = partition.getAggregateRelatedValue(portal_type=["Software Instance", "Slave Instance"])
if si:
  person = si.getSpecialiseValue().getDestinationSectionValue()
  return '<a href="%s?editable_mode:int=1">%s</a>' % (person.getRelativeUrl(), person.getTitle())
