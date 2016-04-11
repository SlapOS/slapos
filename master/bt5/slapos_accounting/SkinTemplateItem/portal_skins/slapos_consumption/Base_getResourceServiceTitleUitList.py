cpu_resource = context.service_module.cpu_load_percent
memory_resource = context.service_module.memory_used
disk_resource = context.service_module.disk_used

return [(cpu_resource.getTitle(), cpu_resource.getUid()),
        (disk_resource.getTitle(), disk_resource.getUid()),
        (memory_resource.getTitle(), memory_resource.getUid())]
