def reindexRecursively(document, after_tag=None):
  tag = document.getPath() + '_reindex'
  document.activate(after_tag=after_tag).reindexObject(activate_kw=dict(tag=tag))
  for subdocument in document.getPredecessorValueList(portal_type='Software Instance'):
    if subdocument.getValidationState() != 'invalidated':
      reindexRecursively(subdocument, tag)

reindexRecursively(state_change['object'],)
