select_dict= {'delivery_uid': None}
kw['select_dict']=select_dict
kw['left_join_list']=select_dict.keys()
kw['delivery_uid']=None
kw['group_by']=('uid',)
if src__==0:
  return context.portal_catalog(**kw)
else:
  return context.portal_catalog(src__=1, **kw)
