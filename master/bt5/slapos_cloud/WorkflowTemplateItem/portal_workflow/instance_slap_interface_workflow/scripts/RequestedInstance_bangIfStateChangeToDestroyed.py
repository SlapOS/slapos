instance = state_change['object']
if (instance.getPortalType() in ["Software Instance", "Slave Instance"]) and (instance.getSlapState() != 'destroy_requested'):
  instance.bang(bang_tree=False, comment="State changed from %s to destroy_requested" % instance.getSlapState())
