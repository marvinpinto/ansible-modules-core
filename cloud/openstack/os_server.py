#!/usr/bin/python
# coding: utf-8 -*-

# Copyright (c) 2014 Hewlett-Packard Development Company, L.P.
# Copyright (c) 2013, Benno Joy <benno@ansible.com>
# Copyright (c) 2013, John Dewey <john@dewey.ws>
#
# This module is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this software.  If not, see <http://www.gnu.org/licenses/>.


try:
    import shade
    from shade import meta
    HAS_SHADE = True
except ImportError:
    HAS_SHADE = False


DOCUMENTATION = '''
---
module: os_server
short_description: Create/Delete Compute Instances from OpenStack
extends_documentation_fragment: openstack
version_added: "2.0"
author: "Monty Taylor (@emonty)"
description:
   - Create or Remove compute instances from OpenStack.
options:
   name:
     description:
        - Name that has to be given to the instance
     required: true
   image:
     description:
        - The name or id of the base image to boot.
     required: true
   image_exclude:
     description:
        - Text to use to filter image names, for the case, such as HP, where
          there are multiple image names matching the common identifying
          portions. image_exclude is a negative match filter - it is text that
          may not exist in the image name. Defaults to "(deprecated)"
   flavor:
     description:
        - The name or id of the flavor in which the new instance has to be
          created. Mutually exclusive with flavor_ram
     required: false
     default: 1
   flavor_ram:
     description:
        - The minimum amount of ram in MB that the flavor in which the new
          instance has to be created must have. Mutually exclusive with flavor.
     required: false
     default: 1
   flavor_include:
     description:
        - Text to use to filter flavor names, for the case, such as Rackspace,
          where there are multiple flavors that have the same ram count.
          flavor_include is a positive match filter - it must exist in the
          flavor name.
   key_name:
     description:
        - The key pair name to be used when creating a instance
     required: false
     default: None
   security_groups:
     description:
        - The name of the security group to which the instance should be added
     required: false
     default: None
   nics:
     description:
        - A list of networks to which the instance's interface should
          be attached. Networks may be referenced by net-id or net-name.
     required: false
     default: None
   public_ip:
     description:
        - Ensure instance has public ip however the cloud wants to do that
     required: false
     default: 'yes'
   auto_floating_ip:
     description:
        - If the module should automatically assign a floating IP
     required: false
     default: 'yes'
   floating_ips:
     description:
        - list of valid floating IPs that pre-exist to assign to this node
     required: false
     default: None
   floating_ip_pools:
     description:
        - list of floating IP pools from which to choose a floating IP
     required: false
     default: None
   meta:
     description:
        - A list of key value pairs that should be provided as a metadata to
          the new instance.
     required: false
     default: None
   wait:
     description:
        - If the module should wait for the instance to be created.
     required: false
     default: 'yes'
   timeout:
     description:
        - The amount of time the module should wait for the instance to get
          into active state.
     required: false
     default: 180
   config_drive:
     description:
        - Whether to boot the server with config drive enabled
     required: false
     default: 'no'
   userdata:
     description:
        - Opaque blob of data which is made available to the instance
     required: false
     default: None
   root_volume:
     description:
        - Boot instance from a volume
     required: false
     default: None
   terminate_volume:
     description:
        - If true, delete volume when deleting instance (if booted from volume)
     default: false
   state:
     description:
       - Should the resource be present or absent.
     choices: [present, absent]
     default: present
requirements:
    - "python >= 2.6"
    - "shade"
'''

EXAMPLES = '''
# Creates a new instance and attaches to a network and passes metadata to
# the instance
- os_server:
       state: present
       auth:
         auth_url: https://region-b.geo-1.identity.hpcloudsvc.com:35357/v2.0/
         username: admin
         password: admin
         project_name: admin
       name: vm1
       image: 4f905f38-e52a-43d2-b6ec-754a13ffb529
       key_name: ansible_key
       timeout: 200
       flavor: 4
       nics:
         - net-id: 34605f38-e52a-25d2-b6ec-754a13ffb723
         - net-name: another_network
       meta:
         hostname: test1
         group: uge_master

# Creates a new instance in HP Cloud AE1 region availability zone az2 and
# automatically assigns a floating IP
- name: launch a compute instance
  hosts: localhost
  tasks:
  - name: launch an instance
    os_server:
      state: present
      auth:
        auth_url: https://region-b.geo-1.identity.hpcloudsvc.com:35357/v2.0/
        username: username
        password: Equality7-2521
        project_name: username-project1
      name: vm1
      region_name: region-b.geo-1
      availability_zone: az2
      image: 9302692b-b787-4b52-a3a6-daebb79cb498
      key_name: test
      timeout: 200
      flavor: 101
      security_groups: default
      auto_floating_ip: yes

# Creates a new instance in named cloud mordred availability zone az2
# and assigns a pre-known floating IP
- name: launch a compute instance
  hosts: localhost
  tasks:
  - name: launch an instance
    os_server:
      state: present
      cloud: mordred
      name: vm1
      availability_zone: az2
      image: 9302692b-b787-4b52-a3a6-daebb79cb498
      key_name: test
      timeout: 200
      flavor: 101
      floating-ips:
        - 12.34.56.79

# Creates a new instance with 4G of RAM on Ubuntu Trusty, ignoring
# deprecated images
- name: launch a compute instance
  hosts: localhost
  tasks:
  - name: launch an instance
    os_server:
      name: vm1
      state: present
      cloud: mordred
      region_name: region-b.geo-1
      image: Ubuntu Server 14.04
      image_exclude: deprecated
      flavor_ram: 4096

# Creates a new instance with 4G of RAM on Ubuntu Trusty on a Performance node
- name: launch a compute instance
  hosts: localhost
  tasks:
  - name: launch an instance
    os_server:
      name: vm1
      cloud: rax-dfw
      state: present
      image: Ubuntu 14.04 LTS (Trusty Tahr) (PVHVM)
      flavor_ram: 4096
      flavor_include: Performance
'''


def _exit_hostvars(module, cloud, server, changed=True):
    hostvars = meta.get_hostvars_from_server(cloud, server)
    module.exit_json(
        changed=changed, server=server, id=server.id, openstack=hostvars)


def _network_args(module, cloud):
    args = []
    for net in module.params['nics']:
        if net.get('net-id'):
            args.append(net)
        elif net.get('net-name'):
            by_name = cloud.get_network(net['net-name'])
            if not by_name:
                module.fail_json(
                    msg='Could not find network by net-name: %s' %
                    net['net-name'])
            args.append({'net-id': by_name['id']})
        elif net.get('port-id'):
            args.append(net)
        elif net.get('port-name'):
            by_name = cloud.get_port(net['port-name'])
            if not by_name:
                module.fail_json(
                    msg='Could not find port by port-name: %s' %
                    net['port-name'])
            args.append({'port-id': by_name['id']})
    return args


def _delete_server(module, cloud):
    try:
        cloud.delete_server(
            module.params['name'], wait=module.params['wait'],
            timeout=module.params['timeout'])
    except Exception as e:
        module.fail_json(msg="Error in deleting vm: %s" % e.message)
    module.exit_json(changed=True, result='deleted')


def _create_server(module, cloud):
    flavor = module.params['flavor']
    flavor_ram = module.params['flavor_ram']
    flavor_include = module.params['flavor_include']

    image_id = None
    if not module.params['root_volume']:
        image_id = cloud.get_image_id(
            module.params['image'], module.params['image_exclude'])

    if flavor:
        flavor_dict = cloud.get_flavor(flavor)
        if not flavor_dict:
            module.fail_json(msg="Could not find flavor %s" % flavor) 
    else:
        flavor_dict = cloud.get_flavor_by_ram(flavor_ram, flavor_include)
        if not flavor_dict:
            module.fail_json(msg="Could not find any matching flavor") 

    nics = _network_args(module, cloud)

    bootkwargs = dict(
        name=module.params['name'],
        image=image_id,
        flavor=flavor_dict['id'],
        nics=nics,
        meta=module.params['meta'],
        security_groups=module.params['security_groups'].split(','),
        userdata=module.params['userdata'],
        config_drive=module.params['config_drive'],
    )
    for optional_param in ('region_name', 'key_name', 'availability_zone'):
        if module.params[optional_param]:
            bootkwargs[optional_param] = module.params[optional_param]

    server = cloud.create_server(
        ip_pool=module.params['floating_ip_pools'],
        ips=module.params['floating_ips'],
        auto_ip=module.params['auto_floating_ip'],
        root_volume=module.params['root_volume'],
        terminate_volume=module.params['terminate_volume'],
        wait=module.params['wait'], timeout=module.params['timeout'],
        **bootkwargs
    )

    _exit_hostvars(module, cloud, server)


def _delete_floating_ip_list(cloud, server, extra_ips):
    for ip in extra_ips:
        cloud.nova_client.servers.remove_floating_ip(
            server=server.id, address=ip)


def _check_floating_ips(module, cloud, server):
    changed = False

    auto_floating_ip = module.params['auto_floating_ip']
    floating_ips = module.params['floating_ips']
    floating_ip_pools = module.params['floating_ip_pools']

    if floating_ip_pools or floating_ips or auto_floating_ip:
        ips = openstack_find_nova_addresses(server.addresses, 'floating')
        if not ips:
            # If we're configured to have a floating but we don't have one,
            # let's add one
            server = cloud.add_ips_to_server(
                server,
                auto_ip=auto_floating_ip,
                ips=floating_ips,
                ip_pool=floating_ip_pools,
            )
            changed = True
        elif floating_ips:
            # we were configured to have specific ips, let's make sure we have
            # those
            missing_ips = []
            for ip in floating_ips:
                if ip not in ips:
                    missing_ips.append(ip)
            if missing_ips:
                server = cloud.add_ip_list(server, missing_ips)
                changed = True
            extra_ips = []
            for ip in ips:
                if ip not in floating_ips:
                    extra_ips.append(ip)
            if extra_ips:
                _delete_floating_ip_list(cloud, server, extra_ips)
                changed = True
    return (changed, server)


def _get_server_state(module, cloud):
    state = module.params['state']
    server = cloud.get_server(module.params['name'])
    if server and state == 'present':
        if server.status not in ('ACTIVE', 'SHUTOFF', 'PAUSED', 'SUSPENDED'):
            module.fail_json(
                msg="The instance is available but not Active state: "
                    + server.status)
        (ip_changed, server) = _check_floating_ips(module, cloud, server)
        _exit_hostvars(module, cloud, server, ip_changed)
    if server and state == 'absent':
        return True
    if state == 'absent':
        module.exit_json(changed=False, result="not present")
    return True


def main():

    argument_spec = openstack_full_argument_spec(
        name                            = dict(required=True),
        image                           = dict(default=None),
        image_exclude                   = dict(default='(deprecated)'),
        flavor                          = dict(default=None),
        flavor_ram                      = dict(default=None, type='int'),
        flavor_include                  = dict(default=None),
        key_name                        = dict(default=None),
        security_groups                 = dict(default='default'),
        nics                            = dict(default=[], type='list'),
        meta                            = dict(default=None),
        userdata                        = dict(default=None),
        config_drive                    = dict(default=False, type='bool'),
        auto_floating_ip                = dict(default=True, type='bool'),
        floating_ips                    = dict(default=None),
        floating_ip_pools               = dict(default=None),
        root_volume                     = dict(default=None),
        terminate_volume                = dict(default=False, type='bool'),
        state                           = dict(default='present', choices=['absent', 'present']),
    )
    module_kwargs = openstack_module_kwargs(
        mutually_exclusive=[
            ['auto_floating_ip', 'floating_ips'],
            ['auto_floating_ip', 'floating_ip_pools'],
            ['floating_ips', 'floating_ip_pools'],
            ['flavor', 'flavor_ram'],
            ['image', 'root_volume'],
        ],
    )
    module = AnsibleModule(argument_spec, **module_kwargs)

    if not HAS_SHADE:
        module.fail_json(msg='shade is required for this module')

    state = module.params['state']
    image = module.params['image']
    root_volume = module.params['root_volume']
    flavor = module.params['flavor']
    flavor_ram = module.params['flavor_ram']

    if state == 'present':
        if not (image or root_volume):
            module.fail_json(
                msg="Parameter 'image' or 'root_volume' is required "
                    "if state == 'present'"
            )
        if not flavor and not flavor_ram:
            module.fail_json(
                msg="Parameter 'flavor' or 'flavor_ram' is required "
                    "if state == 'present'"
            )

    try:
        cloud_params = dict(module.params)
        cloud_params.pop('userdata', None)
        cloud = shade.openstack_cloud(**cloud_params)

        if state == 'present':
            _get_server_state(module, cloud)
            _create_server(module, cloud)
        elif state == 'absent':
            _get_server_state(module, cloud)
            _delete_server(module, cloud)
    except shade.OpenStackCloudException as e:
        module.fail_json(msg=e.message, extra_data=e.extra_data)

# this is magic, see lib/ansible/module_common.py
from ansible.module_utils.basic import *
from ansible.module_utils.openstack import *
if __name__ == '__main__':
    main()
