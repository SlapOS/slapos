movement = context

movement = context

if not movement.SimulationMovement_testCommonRule(rule):
  return False

# XXX hardcoded
receivable_account_type_list = ('asset/receivable',)
payable_account_type_list = ('liability/payable',)

if movement.getQuantity() == 0:
  # do not create empty payment movements
  return False

for account in (movement.getSourceValue(portal_type='Account'),
                movement.getDestinationValue(portal_type='Account')):
  if account is not None:
    account_type = account.getAccountType()
    if account_type in receivable_account_type_list or \
        account_type in payable_account_type_list:
      return True

return False
