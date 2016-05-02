"""
  This script may contains specific prototyping code for 
  get master done for resilience.
"""

title = context.getTitle()

if not (title.startswith("kvm") or title.startswith("runner")):
  # This instance is not a clone from resilience
  return None 

hosting_subscription = context.getSpecialiseValue()

for instance in hosting_subscription.getSpecialiseRelatedValueList(
   portal_type="Software Instance"):
  if instance.getTitle() in ["kvm0", "runner0"]:
    return instance

return None
