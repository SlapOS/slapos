DELETE FROM roles_and_users
<dtml-var sql_delimiter>
INSERT INTO roles_and_users (uid, allowedRolesAndUsers) VALUES
<dtml-in prefix="role" expr="ERP5Site_getSecurityUidListForRecreateTable()">
(<dtml-sqlvar sequence-key type="int">,<dtml-sqlvar expr="role_item" type="string">)<dtml-if sequence-end><dtml-else>,</dtml-if>
</dtml-in>