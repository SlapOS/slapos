select 
  distinct catalog.security_uid, path, portal_type, uid  

from 
  catalog 

where 
  portal_type != "Business Template" 
  and path not like "deleted" 
  and not exists (
     select  
       roles_and_users.uid 
     from 
       roles_and_users 
    where 
       catalog.security_uid = roles_and_users.uid
    )