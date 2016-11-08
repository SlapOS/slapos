mapping_dict = {}

map = {"function_common_content": "deploy-Function.Common", 
       "base_setup_content": "deploy-Base.Setup",
       "slapos_install_content": "deploy-Vifib.Channel",
       "slapos_testing_content": "deploy-Testing.Channel",
       "slapos_unstable_content": "deploy-Unstable.Channel"}

portal = context.getPortalObject()

for m, reference in map.iteritems():
  doc = portal.portal_catalog.getResultValue(reference=reference,
                                    portal_type="Web Page",
                                    validation_state="published")

  mapping_dict[m] = doc.getTextContent()

return mapping_dict
