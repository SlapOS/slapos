# Module kslap provides utility routines for dealing with SlapOS.

# ref_of_instance returns reference an instance was requested with
def ref_of_instance(inst):
    i_comp_id = inst.slap_computer_id
    i_part_id = inst.slap_computer_partition_id
    for x in slap.getOpenOrderDict().values():      # XXX linear search
        if x._computer_reference == i_comp_id  and  \
           x._reference          == i_part_id:
            return x._partition_reference
    raise KeyError('not found reference of instance_guid=%s-%s' % (i_comp_id, i_part_id))
