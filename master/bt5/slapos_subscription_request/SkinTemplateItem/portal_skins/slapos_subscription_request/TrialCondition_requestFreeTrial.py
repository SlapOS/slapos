from zExceptions import Unauthorized
if REQUEST is None:
  raise Unauthorized

if REQUEST.other['method'] != "GET":
  raise ValueError("Method is not GET but a " + REQUEST.other['method'])

else:
  if default_email_text is None:
    raise ValueError("Please Provide some email!")

  user_input_dict = {
    "input0": default_input0,
    "input1": default_input1}

  return context.TrialCondition_requestFreeTrialProxy(
    default_email_text, user_input_dict=user_input_dict, batch_mode=0)
