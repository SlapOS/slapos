return [x for x in context.contentValues(**kw) if x.getSlapState() == 'busy']
