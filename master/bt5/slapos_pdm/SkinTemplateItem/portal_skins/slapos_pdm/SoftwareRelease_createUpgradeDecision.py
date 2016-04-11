from DateTime import DateTime

portal = context.getPortalObject()
software_release = context

source_product = portal.restrictedTraverse(source_url, None)
if not source_product:
  return

portal_type = source_product.getPortalType()
if portal_type == 'Computer':
  person_url = source_product.getSourceAdministration()
elif portal_type == 'Hosting Subscription':
  person_url = source_product.getDestinationSection()
else:
  return

if not person_url:
  return

upgrade_decision = portal.upgrade_decision_module.\
            template_upgrade_decision.Base_createCloneDocument(batch_mode=1)

upgrade_decision.edit(title=title)

upgrade_decision.setDestinationSection(person_url)
upgrade_decision.setDestinationDecision(person_url)

decision_line_list = upgrade_decision.contentValues(
                    portal_type='Upgrade Decision Line')
if len(decision_line_list) > 0:
  decision_line = decision_line_list[0]
else:
  decision_line = upgrade_decision.newContent(
                    portal_type='Upgrade Decision Line')

decision_line.edit(
  title='Request decision upgrade for %s on %s %s' % (
    software_release.getTitle(), portal_type, source_product.getReference()),
  aggregate=[source_url, software_release.getRelativeUrl()])

return upgrade_decision
