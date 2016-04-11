kw['simulation_state'] = ['validated','submitted']
kw['sort_on'] = [('modification_date', 'DESC'),]
return context.searchFolder(**kw)
