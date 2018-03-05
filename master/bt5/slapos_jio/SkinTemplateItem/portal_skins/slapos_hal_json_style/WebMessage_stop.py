from zExceptions import Unauthorized
portal = context.getPortalObject()
person = portal.ERP5Site_getAuthenticatedMemberPersonValue()

# XXX Proxy role is Manager so user to open ticket which is closed.
# We check permissions
if not person:
  raise Unauthorized("You need to be logged in before modify this object!")

ticket = context.getFollowUpValue()
if ticket.getDestinationDecision() != person.getRelativeUrl():
  raise Unauthorized

context.stop(comment="Submitted from the renderjs app")
if portal.portal_workflow.isTransitionPossible(ticket, "validate"):
  ticket.validate(comment="See %s" % context.getRelativeUrl())
