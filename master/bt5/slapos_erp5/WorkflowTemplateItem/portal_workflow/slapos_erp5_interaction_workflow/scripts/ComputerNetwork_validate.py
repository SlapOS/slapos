computer_network = state_object["object"]

if computer_network.getValidationState() == "draft":
  computer_network.validate()
