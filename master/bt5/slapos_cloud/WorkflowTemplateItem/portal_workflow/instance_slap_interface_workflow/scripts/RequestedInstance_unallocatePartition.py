instance = state_change['object']
assert instance.getPortalType() in ["Software Instance", "Slave Instance"]
assert instance.getAggregate("") != ""

instance.edit(aggregate="", activate_kw={'tag': 'allocate_%s' % instance.getAggregate()})
