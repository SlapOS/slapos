# Module kslap provides utility routines for dealing with SlapOS.

# ref_of_instance returns reference an instance was requested with.
def ref_of_instance(slap, inst):
    i_comp_id = inst.slap_computer_id
    i_part_id = inst.slap_computer_partition_id
    for x in slap.getOpenOrderDict().values():      # XXX linear search
        if x._computer_reference == i_comp_id  and  \
           x._reference          == i_part_id:
            return x._partition_reference
    raise KeyError('not found reference of instance_guid=%s-%s' % (i_comp_id, i_part_id))


# instance_by_ref returns instance corresponding to specified reference.
def instance_by_ref(slap, ref):
    for x in slap.getOpenOrderDict().values():      # XXX linear search
        if x._partition_reference == ref:
            return x
    raise KeyError('not found instance coresponding to reference %s' % ref)

    # XXX vvv does not return information about slaves, nor information about
    # to which comp/partition the instance is deployed
    """
    o = slap.registerOpenOrder()
    return o._hateoas_navigator.getInstanceTreeRootSoftwareInstanceInformation(ref)
    inst = slap.registerOpenOrder().getInformation(partition_reference=ref)
    return inst
    """
