##############################################################################
#
# Copyright (c) 2011 Vifib SARL and Contributors. All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

import os
import pkg_resources
from logging import Formatter

class KumoTestBed(object):

  def run_default(self, recipe):
    run_kumo_cloud(recipe)

  def run_kumo_cloud(self, recipe):
    """ Deploy kumofs system on a cloud. """

    kumo_cloud_config = {}
    kumo_cloud_config.update(recipe.options)
    kumo_cloud_config.update(recipe.parameter_dict)

    kumo_cloud_config['address'] = recipe.getGlobalIPv6Address()
    kumo_cloud_config['report_path'] = recipe.log_directory
    
    kumo_cloud_config.setdefault('max_server', 4)
    kumo_cloud_config.setdefault('max_tester', 5)
    kumo_cloud_config.setdefault('nb_thread', 32)
    kumo_cloud_config.setdefault('nb_request', 1024000)
    kumo_cloud_config.setdefault('erp5_publish_url', '')
    kumo_cloud_config.setdefault('erp5_publish_project', '')
    
    computer_guid_list = []
    computer_guid_list.append("COMP-23") # manager
    computer_guid_list.append("COMP-13") # server 1
    computer_guid_list.append("COMP-14") # server 2
    computer_guid_list.append("COMP-20") # server 3
    computer_guid_list.append("COMP-19") # server 4
    computer_guid_list.append("COMP-23") # tester 1
    computer_guid_list.append("COMP-22") # tester 2
    computer_guid_list.append("COMP-14") # tester 3
    computer_guid_list.append("COMP-20") # tester 4
    computer_guid_list.append("COMP-19") # tester 5
    
    kumo_cloud_config.setdefault('computer_guid_list', ":".join(computer_guid_list))
    
    kumo_cloud_config['software_release_url'] = recipe.software_release_url
    kumo_cloud_config['server_url'] = recipe.server_url
    kumo_cloud_config['key_file'] = recipe.key_file
    kumo_cloud_config['cert_file'] = recipe.cert_file
    kumo_cloud_config['computer_id'] = recipe.computer_id
    kumo_cloud_config['computer_partition_id'] = recipe.computer_partition_id
    kumo_cloud_config['plugin_name'] = 'kumo'

    kumo_cloud_connection = {}
    kumo_cloud_connection['url'] = "http://["+kumo_cloud_config['address']+"]:5000/"
    kumo_cloud_connection['computer_guid_list'] = kumo_cloud_config['computer_guid_list']
    recipe.computer_partition.setConnectionDict(kumo_cloud_connection)

    nosqltester_manager_wrapper_template_location = pkg_resources.resource_filename(
                                             __name__, os.path.join(
                                             'template', 'kumotester_manager_run.in'))
    nosqltester_manager_runner_path = recipe.createRunningWrapper("kumotester_manager",
          recipe.substituteTemplate(nosqltester_manager_wrapper_template_location, kumo_cloud_config))

    return [nosqltester_manager_runner_path]

  def run_all(self, recipe):
    """ Run all services on one machine. """
    all_config = {}
    all_config.update(recipe.options)

    ipaddress = "[%s]" % recipe.getGlobalIPv6Address()

    all_config['manager_address'] = ipaddress
    all_config['manager_port'] = 19700
    all_config['server_address'] = ipaddress
    all_config['server_port'] = 19800
    all_config['server_listen_port'] = 19900
    all_config['server_storage'] = os.path.join(recipe.data_root_directory, "kumodb.tch")
    all_config['gateway_address'] = ipaddress
    all_config['gateway_port'] = 11411
    all_config['manager_log'] = os.path.join(recipe.log_directory, "kumo-manager.log")
    all_config['server_log'] = os.path.join(recipe.log_directory, "kumo-server.log")
    all_config['gateway_log'] = os.path.join(recipe.log_directory, "kumo-gateway.log")

    manager_wrapper_template_location = pkg_resources.resource_filename(
                                             __name__, os.path.join(
                                             'template', 'kumo_manager_run.in'))
    manager_runner_path = recipe.createRunningWrapper("kumo-manager",
          recipe.substituteTemplate(manager_wrapper_template_location, all_config))
    server_wrapper_template_location = pkg_resources.resource_filename(
                                             __name__, os.path.join(
                                             'template', 'kumo_server_run.in'))
    server_runner_path = recipe.createRunningWrapper("kumo-server",
          recipe.substituteTemplate(server_wrapper_template_location, all_config))
    gateway_wrapper_template_location = pkg_resources.resource_filename(
                                             __name__, os.path.join(
                                             'template', 'kumo_gateway_run.in'))
    gateway_runner_path = recipe.createRunningWrapper("kumo-gateway",
          recipe.substituteTemplate(gateway_wrapper_template_location, all_config))

    return [manager_runner_path, server_runner_path, gateway_runner_path]

  def run_kumo_manager(self, recipe):
    """ Run the kumofs manager. """
    manager_config = {}
    manager_config.update(recipe.options)

    manager_config['manager_address'] = "[%s]" % recipe.getGlobalIPv6Address()
    manager_config['manager_port'] = 19700
    manager_config['manager_log'] = os.path.join(recipe.log_directory, "kumo-manager.log")

    manager_connection = {}
    manager_connection['address'] = manager_config['manager_address']
    manager_connection['port'] = manager_config['manager_port']
    recipe.computer_partition.setConnectionDict(manager_connection)

    manager_wrapper_template_location = pkg_resources.resource_filename(
                                             __name__, os.path.join(
                                             'template', 'kumo_manager_run.in'))
    manager_runner_path = recipe.createRunningWrapper("kumo-manager",
          recipe.substituteTemplate(manager_wrapper_template_location, manager_config))

    return [manager_runner_path]

  def run_kumo_server(self, recipe):
    """ Run the kumofs server. """
    server_config = {}
    server_config.update(recipe.options)
    server_config.update(recipe.parameter_dict)

    server_config['server_address'] = "[%s]" % recipe.getGlobalIPv6Address()
    server_config['server_port'] = 19800
    server_config['server_listen_port'] = 19900
    server_config['server_storage'] = os.path.join(recipe.var_directory,"kumodb.tch")
    server_config['server_log'] = os.path.join(recipe.log_directory, "kumo-server.log")

    server_connection = {}
    server_connection['address'] = server_config['server_address']
    recipe.computer_partition.setConnectionDict(server_connection)

    server_wrapper_template_location = pkg_resources.resource_filename(
                                             __name__, os.path.join(
                                             'template', 'kumo_server_run.in'))
    server_runner_path = recipe.createRunningWrapper("kumo-server",
          recipe.substituteTemplate(server_wrapper_template_location, server_config))

    return [server_runner_path]

  def run_kumo_gateway(self, recipe):
    """ Run the kumofs gateway. """
    gateway_config = {}
    gateway_config.update(recipe.options)
    gateway_config.update(recipe.parameter_dict)

    gateway_config['gateway_address'] = "[%s]" % recipe.getGlobalIPv6Address()
    gateway_config['gateway_port'] = 11411
    gateway_config['gateway_log'] = os.path.join(recipe.log_directory, "kumo-gateway.log")

    gateway_connection = {}
    gateway_connection['address'] = gateway_config['gateway_address']
    gateway_connection['port'] = gateway_config['gateway_port']
    recipe.computer_partition.setConnectionDict(gateway_connection)

    gateway_wrapper_template_location = pkg_resources.resource_filename(
                                             __name__, os.path.join(
                                             'template', 'kumo_gateway_run.in'))
    gateway_runner_path = recipe.createRunningWrapper("kumo-gateway",
          recipe.substituteTemplate(gateway_wrapper_template_location, gateway_config))

    return [gateway_runner_path]

  def run_kumo_tester(self, recipe):
    """ Run the kumofs tester. """
    tester_config = {}
    tester_config.update(recipe.options)
    tester_config.update(recipe.parameter_dict)

    tester_config['tester_address'] = recipe.getGlobalIPv6Address()
    # tester_config['url'] = "http://%s:5000/" % tester_config['tester_address']
    # tester_config['start_url'] = "http://%s:5000/start" % tester_config['tester_address']
    tester_config['report_path'] = recipe.log_directory
    config_dict['binary'] = "%s -g -l %s -p %s -t %s %s" % (config_dict['memstrike_binary'],
                                                            config_dict['gateway_address'].strip("[]"),
                                                            str(config_dict['gateway_port']),
                                                            str(config_dict['nb_thread']),
                                                            str(config_dict['nb_request']))
    tester_config['log_directory'] = recipe.log_directory
    tester_config['compress_method'] = "bz2"

    tester_connection = {}
    tester_connection['url'] = "http://%s:5000/" % tester_config['tester_address']
    recipe.computer_partition.setConnectionDict(tester_connection)

    tester_wrapper_template_location = pkg_resources.resource_filename(
                                             'slapos.recipe.nosqltestbed', os.path.join(
                                             'template', 'nosqltester_run.in'))
    tester_runner_path = recipe.createRunningWrapper("nosqltester",
          recipe.substituteTemplate(tester_wrapper_template_location, tester_config))

    return [tester_runner_path]

  def run_kumo_tester_and_gateway(self, recipe):
    """ Run the kumofs tester and gateway on the same partition. """
    address = recipe.getGlobalIPv6Address()

    config_dict = {}
    config_dict.update(recipe.options)
    config_dict.update(recipe.parameter_dict)

    # Gateway part
    config_dict['gateway_address'] = "[%s]" % address
    config_dict['gateway_port'] = 11411
    config_dict['gateway_log'] = os.path.join(recipe.log_directory, "kumo-gateway.log")

    # Tester part
    config_dict['tester_address'] = address
    config_dict['report_path'] = recipe.log_directory
    config_dict['binary'] = "%s -g -l %s -p %s -t %s %s" % (config_dict['memstrike_binary'],
                                                            config_dict['gateway_address'].strip("[]"),
                                                            str(config_dict['gateway_port']),
                                                            str(config_dict['nb_thread']),
                                                            str(config_dict['nb_request']))
    config_dict['log_directory'] = recipe.log_directory
    config_dict['compress_method'] = "bz2"

    connection_dict = {}
    # connection_dict['address'] = config_dict['gateway_address']
    # connection_dict['port'] = config_dict['gateway_port']
    connection_dict['url'] = "http://%s:5000/" % config_dict['tester_address']
    recipe.computer_partition.setConnectionDict(connection_dict)

    gateway_wrapper_template_location = pkg_resources.resource_filename(
                                             __name__, os.path.join(
                                             'template', 'kumo_gateway_run.in'))
    gateway_runner_path = recipe.createRunningWrapper("kumo-gateway",
          recipe.substituteTemplate(gateway_wrapper_template_location, config_dict))

    tester_wrapper_template_location = pkg_resources.resource_filename(
                                             'slapos.recipe.nosqltestbed', os.path.join(
                                             'template', 'nosqltester_run.in'))
    tester_runner_path = recipe.createRunningWrapper("nosqltester",
          recipe.substituteTemplate(tester_wrapper_template_location, config_dict))

    return [gateway_runner_path, tester_runner_path]

  def run_memstrike_set(self, recipe):
    """ Run memstrike in set mode. """
    memstrike_config = {}
    memstrike_config.update(recipe.options)
    memstrike_config.update(recipe.parameter_dict)

    memstrike_config['gateway_address'] = memstrike_config['gateway_address'].strip("[]")

    memstrike_connection = {}
    memstrike_connection['status'] = "OK"
    recipe.computer_partition.setConnectionDict(memstrike_connection)

    memstrike_wrapper_template_location = pkg_resources.resource_filename(
                                             __name__, os.path.join(
                                             'template', 'memstrike_run.in'))
    memstrike_runner_path = recipe.createRunningWrapper("memstrike_set",
          recipe.substituteTemplate(memstrike_wrapper_template_location, memstrike_config))

    return [memstrike_runner_path]

