ticket = state_object["object"]

from DateTime import DateTime
portal = context.getPortalObject()

# XXX unhardcode the trade condition, by adding a preference
if ticket.getSpecialise() != "sale_trade_condition_module/slapos_ticket_trade_condition":
  return

if ticket.getSimulationState() != "draft":
  return

trade_condition = portal.sale_trade_condition_module.slapos_ticket_trade_condition

ticket.edit(
  source_section = trade_condition.getSourceSection(),
  source_trade=trade_condition.getSourceSection(),
  source=trade_condition.getSource())

ticket.setStartDate(DateTime())

ticket.validate()

web_message = context.Ticket_createInitialEvent()

web_message.edit(
  title=ticket.getTitle(),
  content_type="text/plain",
  text_content=ticket.getDescription(),
  source=ticket.getDestinationDecision(),
  destination=trade_condition.getSource(),
  resource=ticket.getResource(),
  start_date=DateTime(),
  follow_up_value=ticket,
)
web_message.stop()
