locked = context.getSlapState() == 'locked'
customer_uid = context.getUid()
balance = context.portal_simulation.getInventoryAssetPrice(
  node_category='account_type/asset/receivable',
  simulation_state=simulation_state,
  section_uid=section_uid,
  mirror_section_uid=customer_uid)

if maximum_balance > balance:
  # customer reached his balance, shall be locked
  if not locked and operation == 'lock':
      context.lock(comment="Balance value is %s" % balance)
      return

# check ongoing payments and check that date if is acceptable, if not lock
if context.portal_simulation.getInventoryAssetPrice(
  parent_portal_type='Payment Transaction',
  node_category='account_type/asset/receivable',
  simulation_state=ongoing_simulation_state,
  section_uid=section_uid,
  mirror_section_uid=customer_uid,
  at_date=maximum_due_date,
  ) > 0:
    # there are ongoing old payments, shall be locked
    if not locked and operation == 'lock':
        context.lock(comment="Payment transaction not paid for more than %s days" % maximum_due_date)
elif balance >= 0.0:
   # there are no ongoing payments and customer owns nothing
   if locked and operation == 'unlock':
     context.unlock()
