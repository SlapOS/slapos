"""
  Include information of the sender/recipient to clarify.
"""

return """

Sender: %s
Recipient: %s

Content:

%s

""" % (context.getSourceTitle(""), 
       ",".join(context.getDestinationTitleList()), 
       context.getTextContent())
