# Module kslap provides utility routines for dealing with SlapOS.

# after importing users should do kslap.init(slap)
slap = None
def init(slap_):
    global slap
    slap = slap_

# ref_of_instance returns reference an instance was requested with.
def ref_of_instance(inst):
    i_comp_id = inst.slap_computer_id
    i_part_id = inst.slap_computer_partition_id
    for x in slap.getOpenOrderDict().values():      # XXX linear search
        if x._computer_reference == i_comp_id  and  \
           x._reference          == i_part_id:
            return x._partition_reference
    raise KeyError('not found reference of instance_guid=%s-%s' % (i_comp_id, i_part_id))


# instance_by_ref returns instance corresponding to specified reference.
def instance_by_ref(ref):
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

# iSIM adds to core a shared SIM instance with specified number.
def iSIM(core, sim_n):
    core_ref  = ref_of_instance(core)
    core_guid = core.getInstanceGuid()
    core_sr   = core.getSoftwareRelease()
    sim = request(core_sr,
        software_type="core-network",
        partition_reference="%s/sim%d" % (core_ref, sim_n),
        shared=True,
        filter_kw={"instance_guid": core_guid},
        partition_parameter_kw={"_": json.dumps({
            "sim_algo": "milenage",
            "imsi": "001010000000%d" % sim_n,
            "opc": "000102030405060708090A0B0C0D0E0F",
            "amf": "0x9001",
            "sqn": "000000000000",
            "k": "00112233445566778899AABBCCDDEEFF",
            "impu": "impu%d" % sim_n,
            "impi": "impi%d@amarisoft.com" % sim_n,
        })})
    return sim

# iENB adds to enb a shared instance with specified reference and parameters.
def iENB(enb, ref, kw):
    enb_ref  = ref_of_instance(enb)
    enb_guid = enb.getInstanceGuid()
    enb_sr   = enb.getSoftwareRelease()
    ishared = request(enb_sr,
        software_type="enb",
        partition_reference=ref,
        shared=True,
        filter_kw={"instance_guid": enb_guid},
        partition_parameter_kw={"_": json.dumps(kw)})
    return ishared
