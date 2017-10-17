""" Simple place for keep the list of business template to install on this project
"""


bt5_update_catalog_list = ('erp5_ingestion_mysql_innodb_catalog',
                           'slapos_cloud', 'erp5_accounting',
                           'erp5_movement_table_catalog')

bt5_installation_list = bt5_update_catalog_list + ('slapos_configurator', 'slapos_erp5')

keep_bt5_id_list = ['erp5_ui_test',
                    'erp5_ui_test_core',
                    'slapos_category',
                    'erp5_secure_payment',
                    'vifib_datas']

return bt5_installation_list, bt5_update_catalog_list, keep_bt5_id_list
