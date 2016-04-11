#We extract informations from SPL
packing_list_dict = {'packing_list_title': context.getTitle()}

#We extract informations from SPLL
sale_packing_list_line_list = [line for line in context.objectValues(
                                       portal_type='Sale Packing List Line')
]

xml_head = ""
xml_movements = ""
xml_foot = ""

xml_head = "<?xml version='1.0' encoding='utf-8'?>" \
           "<journal>" \
           "<transaction type=\"Sale Packing List\">" \
           "<title>%(packing_list_title)s</title>" \
           "<start_date></start_date>" \
           "<stop_date></stop_date>" \
           "<reference></reference>" \
           "<currency></currency>" \
           "<payment_mode></payment_mode>" \
           "<category></category>" \
           "<arrow type=\"Administration\">" \
           "<source></source>" \
           "<destination></destination>" \
           "</arrow>" \
           % packing_list_dict

for sale_packing_list_line in sale_packing_list_line_list:

    packing_list_line_dict = {'packing_list_line_title': sale_packing_list_line.getTitle(),
                              'packing_list_line_resource': sale_packing_list_line.getResourceTitle(),
                              'packing_list_line_reference': sale_packing_list_line.getAggregateValue().getTitle(),
                              'packing_list_line_quantity': sale_packing_list_line.getQuantity(),
                             }

    xml_movements += "<movement>" \
                     "<resource>%(packing_list_line_resource)s</resource>" \
                     "<title>%(packing_list_line_title)s</title>" \
                     "<reference>%(packing_list_line_reference)s</reference>" \
                     "<quantity>%(packing_list_line_quantity)s</quantity>" \
                     "<price>0.00</price>" \
                     "<VAT>None</VAT>" \
                     "<category>None</category>" \
                     "</movement>" \
                     % packing_list_line_dict

xml_foot = "</transaction>" \
           "</journal>"

xml = xml_head + xml_movements + xml_foot
return xml
