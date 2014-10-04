

CONTRIBUTION_MAPPING = {
  "shuttle_ds61_i7" : 0.045,
  "nuc_i7": 0.055
  }

def get_contribution_ratio(model_id, contribution):
  zero_emission_ratio_limit = CONTRIBUTION_MAPPING.get(model_id)
  if zero_emission_ratio_limit is None:
    raise ValueError("Unknown heating contibution")
  
  if contribution < zero_emission_ratio_limit:
    # The machine don't contribute for heating
    return 0
  else:
    # The machine contributes for the heating
    return 100
