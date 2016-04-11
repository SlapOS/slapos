""" 
This script generate a usage report test sample for one or two partitions
"""

# First we check the number of partition to invoice
if number in [1, 2]:

  # We build movements
  movement = """
    <movement>
      <resource>%s</resource>
      <title>%s</title>
      <reference>%s</reference>       
      <quantity>%s</quantity>
      <price>0.00</price>        
      <VAT>None</VAT>
      <category>None</category>
    </movement>"""

  # Then, we create two movements for each partition, one for the CPU consumption, and the other for the memory
  movements = ""
  for nb in range(number):
    if nb == 0:
      movements += movement % ('CPU Consumption', 'Title Sale Packing List Line 1', 'slappart0', '42.42')
      movements += movement % ('Memory Consumption', 'Title Sale Packing List Line 2', 'slappart0', '42.42')
    else:
      movements += movement % ('CPU Consumption', 'Title Sale Packing List Line 1', 'slappart1', '46.46')
      movements += movement % ('Memory Consumption', 'Title Sale Packing List Line 2', 'slappart1', '46.46')

  # Finally, we build the XML usage report
  xml = """<?xml version='1.0' encoding='utf-8'?>
  <journal>
    <transaction type="Sale Packing List">
      <title>Resource consumptions</title>
      <start_date></start_date>
      <stop_date></stop_date>
      <reference></reference>
      <currency></currency>
      <payment_mode></payment_mode>
      <category></category>
      <arrow type="Administration">
        <source></source>
        <destination></destination>
      </arrow>""" + movements + """
    </transaction>
  </journal>"""

  return xml

else:
  return 'This script can generate movements for one or two partitions maximum'
