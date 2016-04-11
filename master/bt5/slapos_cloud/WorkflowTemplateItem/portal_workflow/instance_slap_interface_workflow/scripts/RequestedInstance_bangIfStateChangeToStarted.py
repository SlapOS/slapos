instance = state_change['object']
if (instance.getPortalType() in ["Software Instance", "Slave Instance"]) and (instance.getSlapState() != 'start_requested'):
  instance.bang(bang_tree=False, comment="State changed from %s to start_requested" % instance.getSlapState())
