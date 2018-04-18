#!.venv/bin/python

import os
from jnpr.junos import Device
import napalm
from lxml import etree
from datetime import datetime

def get_isis_db(router, port):

    isis_db = []

    with Device(host = router, 
                user = os.environ['ADUSERNAME'], 
                password = os.environ['ADPASSWORD'], 
                port = port,
                auto_probe = 10, 
                facts = False) as dev:

        response = dev.rpc.get_isis_database_information(extensive = True, level = '2')
        
        isis_database_entries = response.findall('isis-database/isis-database-entry/isis-header')

        for isis_database_entry in isis_database_entries:
            router_id = isis_database_entry.findtext('router-id').strip()
            if router_id != '0.0.0.0':
                isis_db.append(router_id)

    return isis_db

def get_ospf_passive_ints(client):
    ospf_passive_interfaces =[]
    response = client.device.rpc.get_ospf_interface_information(extensive = True)
    passive_ints = response.findall('ospf-interface')
    for _ in passive_ints:
        passive = _.findtext('passive')
        if passive:
            interface = _.findtext('interface-name')
            configured_passive = check_configured_passive(client, interface)
            if configured_passive:
                ospf_passive_interfaces.append(interface)
    ospf_passive_interfaces = list(set(ospf_passive_interfaces))
    return ospf_passive_interfaces

def get_isis_passive_ints(client):
    isis_passive_interfaces =[]
    response = client.device.rpc.get_isis_interface_information()
    passive_ints = response.findall('isis-interface')
    for _ in passive_ints:
        passive = _.findtext('isis-interface-state-two')
        if passive == 'Passive':
            interface = _.findtext('interface-name')
            isis_passive_interfaces.append(interface)
    isis_passive_interfaces = list(set(isis_passive_interfaces))
    return isis_passive_interfaces

def check_configured_passive(client, interface):
    """This is required because of a bug in Junos that shows duplicate interfaces"""
    response = client.device.rpc.get_config()
    ospf_interfaces = response.findall('protocols/ospf/area/interface')
    for ospf_interface in ospf_interfaces:
        if ospf_interface.findtext('name') == interface:
            interface_passive = ospf_interface.findtext('passive')
            if interface_passive is not None:
                return True
            else:
                return False

def main():

    startTime = datetime.now()

    print(f'Getting IS-IS database...')
    isis_db = get_isis_db(router = '10.192.254.18', port = 22)
    print(f'Got {len(isis_db)} entries!\n')

    port = 22

    #isis_db = ['10.0.13.64'] # CCSRTR-SWPE-01

    #isis_db = ['10.192.254.16'] # RBNRTR-HCOR-03

    #isis_db = ['10.0.13.40', '172.28.0.1']

    # SKIPLIST:
    # 10.212.254.48 - ProbeError, is okay
    # 10.0.14.170 - Old Junos, is okay
    # 10.0.30.247 - ProbeError, is okay
    # 10.136.254.16 - HCOR
    # 10.192.254.16 - HCOR
    # 10.192.254.17 - HOCR
    #skiplist = ['10.212.254.48', '10.0.14.170', '10.0.30.247', '10.136.254.16', '10.192.254.16', '10.192.254.17']
    #skiplist = ['10.212.254.48', '10.0.14.170', '10.0.30.247']

    for router in isis_db:

        if router not in skiplist:

            try:

                Device.auto_probe = 10
                driver = napalm.get_network_driver('junos')
                with driver(hostname=router, 
                            username=os.environ['ADUSERNAME'],
                            password=os.environ['ADPASSWORD'], 
                            optional_args={'port': 22, 'config_format': 'set'}) as client:

                    ospf_passive_interfaces = get_ospf_passive_ints(client)
                    isis_passive_interfaces = get_isis_passive_ints(client)  

                    if ospf_passive_interfaces != isis_passive_interfaces and len(ospf_passive_interfaces) != 0:         
                        print(f'{router}: DIFFERENT!\tOSPF: {ospf_passive_interfaces} ISIS: {isis_passive_interfaces}')
                    # else:
                    #     print(f'{router}: SAME!')

            except Exception as e:
                print(f'{router} FAILED: {e}')            
                continue

    print(f'Script completed. It took: {str(datetime.now() - startTime)} to execute.')

if __name__ == '__main__':
    main()
exit()