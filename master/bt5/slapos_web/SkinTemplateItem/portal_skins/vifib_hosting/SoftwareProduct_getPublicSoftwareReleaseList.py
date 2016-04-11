return context.portal_catalog(
    portal_type="Software Release",
    default_aggregate_uid=context.getUid(),
    validation_state=["shared", "shared_alive", "released", 
                      "released_alive", "published", "published_alive"]
    )
