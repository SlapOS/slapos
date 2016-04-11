configuration_save = context.restrictedTraverse(configuration_save_url)

bt5_update_catalog_list = ('erp5_ingestion_mysql_innodb_catalog',
                           'slapos_cloud', 'erp5_accounting',
                           'erp5_movement_table_catalog')

bt5_installation_list = bt5_update_catalog_list + ('slapos_erp5',)
 
for name in bt5_installation_list:
  configuration_save.addConfigurationItem("Standard BT5 Configurator Item",
                                          title=name, bt5_id=name,
                                          update_catalog=(name in bt5_update_catalog_list))
