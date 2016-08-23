kw['simulation_state'] = ['validated','submitted', 'suspended', 'invalidated', 
   # Unfortunally Upgrade decision uses diferent states.
   'confirmed', 'delivered']
kw['sort_on'] = [('modification_date', 'DESC'),]
return context.searchFolder(**kw)
