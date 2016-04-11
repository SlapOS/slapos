resource_uid = context.service_module.disk_used.getUid()

return context.HostingSubscription_getStatForResource(resource_uid, **kw)
