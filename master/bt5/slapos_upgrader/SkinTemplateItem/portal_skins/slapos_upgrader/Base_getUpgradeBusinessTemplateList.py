"""
  This script should returns always two list of Business Template.
   - The first list is to resolve dependencies and upgrade.
   - The second list is what you want to keep. This is useful if we want to keep 
   a old business template without updating it and without removing it
"""

bt5_update_catalog_list = ('erp5_ingestion_mysql_innodb_catalog',
                           'slapos_cloud', 'erp5_accounting',
                           'erp5_movement_table_catalog',
                           'erp5_promise')

bt5_id_list = bt5_update_catalog_list + ('slapos_erp5',)

keep_bt5_id_list = ['erp5_ui_test',
                   'erp5_ui_test_core',
                   'slapos_category',
                   'erp5_secure_payment',
                   'vifib_datas',
                   ]

return bt5_id_list, keep_bt5_id_list
