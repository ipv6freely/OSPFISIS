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

def get_ospf_export(client):
    response = client.device.rpc.get_config()
    ospf_export = response.findtext('protocols/ospf/export')
    # if ospf_export is not None and :
    #     return 'inactive'
    if ospf_export is not None:
        return ospf_export
    else:
        return 'no'

def main():

    startTime = datetime.now()

    print(f'Getting IS-IS database...')
    isis_db = get_isis_db(router = '10.192.254.18', port = 22)
    #isis_db = ['127.0.0.1']
    print(f'Got {len(isis_db)} entries!\n')

    # SKIPLIST:
    # 10.0.14.170 - Old Junos, is okay
    # 10.136.254.16 - HCOR
    # 10.192.254.16 - HCOR
    # 10.192.254.17 - HCOR
    #skiplist = ['10.0.14.170']
    skiplist = []

    #port = 2222
    port = 22

    for router in isis_db:
        if router not in skiplist:

            try:
                driver = napalm.get_network_driver('junos')
                with driver(hostname=router, 
                            username=os.environ['ADUSERNAME'],
                            password=os.environ['ADPASSWORD'], 
                            optional_args={'port': port, 'config_format': 'set'}) as client:

                    router_has_export = get_ospf_export(client)

                    if router_has_export is 'no':
                        pass
                    #     print(f'{isis_db.index(router) + 1:03}/{len(isis_db)}\t{router}\tEXPORT: NO')
                    # elif router_has_export is 'inactive':
                    #     print(f'{isis_db.index(router) + 1:03}/{len(isis_db)}\t{router}\tEXPORT: INACTIVE')
                    else:
                        print(f'{isis_db.index(router) + 1:03}/{len(isis_db)}\t{router}\tEXPORT: {router_has_export}')

            except Exception as e:
                print(f'{router} FAILED: {e}')            
                continue

    print(f'Script completed. It took: {str(datetime.now() - startTime)} to execute.')

if __name__ == '__main__':
    main()
exit()