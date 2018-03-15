import json
trial_configuration = []

def getTermOfServiceContent(document):
  contract = document.getAggregateValue()
  if contract is not None:
    return "<iframe src=./hateoas/%s/getTextContent></iframe>" % contract.getRelativeUrl()
  return ""


def getProductDescription(document):
  product_description = document.getFollowUpValue()
  if product_description is not None:
    return product_description.getTextContent("")
  return ""

for trial_condition in context.portal_catalog(
    portal_type="Trial Condition",
    validation_state="published"):

  input_list = trial_condition.getUserInputList()
  if not input_list:
    input_list = []
  trial_configuration.append(
    {"url": trial_condition.getRelativeUrl(),
     "header": trial_condition.getShortTitle(),
      "name": trial_condition.getTitle(),
      "footer": trial_condition.getDescription(),
      "price": "1 Month Free Trial",
      "terms_of_service": getTermOfServiceContent(trial_condition),
      "product_description": getProductDescription(trial_condition),
      "input_list": input_list
     })

return json.dumps(trial_configuration)
