# -*- coding: utf-8 -*-

import slapos.recipe.addresiliency.renamer

def run(args):
    renamer = slapos.recipe.addresiliency.renamer.Renamer(server_url = args.pop('server_url'),
                                                          key_file = args.pop('key_file'),
                                                          cert_file = args.pop('cert_file'),
                                                          computer_guid = args.pop('computer_id'),
                                                          partition_id = args.pop('partition_id'),
                                                          software_release = args.pop('software'),
                                                          namebase = args.pop('namebase'))

    renamer.failover()


