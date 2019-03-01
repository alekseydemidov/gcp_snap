#!/usr/bin/python3

#from __future__ import print_function
import argparse
from datetime import datetime,timedelta,timezone
import time
from google.oauth2 import service_account
import googleapiclient.discovery

def parse_args():
#Arguments parsing
    parser = argparse.ArgumentParser(description='Taking snapshort of GCP instances')
    parser.add_argument('--project', required=True, help='Project name')
    parser.add_argument('--region', type=str, required=True, help='Region name')
    parser.add_argument('instances', type=str, help='List of instances comma separated')
    parser.add_argument('action', type=str, choices=['create','delete'], help='Action for snapshort: create or delete')
    parser.add_argument('--key-file', required=True, help='Path to service account json file')
    parser.add_argument('-d','--days', type=int, default=7, required=False, help='How old days snapshot should be deleted for instances, 0 - for every snapshots; default 7' )
    parser.add_argument('--ignore', type=str, required=False, default='' ,help='List of snapshots name, what should not be deleted' )
    parser.add_argument('--multiregion', required=False, action="store_true", help='Location store for snapshot will be multiregion')
    parser.add_argument('--debug', required=False, action="store_true", help='Debug information to stdout')
    args = parser.parse_args()
    return args

def debug(msg):
    if debug_status: print (msg)

def google_compute_auth(key_file):
    SCOPES = ['https://www.googleapis.com/auth/compute']
    SERVICE_ACCOUNT_FILE = key_file
    credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    compute = googleapiclient.discovery.build('compute', 'beta',credentials=credentials)
    return compute

def list_zones_name(compute, project, region):
    zones = []
    result = compute.zones().list(project=project,filter="name:"+region+"*").execute()
    debug("Found zones: ")
    for i in result['items']:
        debug(i['name'])
        zones.append(i['name'])
    return zones

### Return list of dictionaries [ { name:'', zone:'', disks:[disk_names] } ]
def instances_get_fact(compute, project, zone):
    instances_fact = []
    result = compute.instances().list(project=project, zone=zone).execute()
    if 'items' in result:
        for i in result['items']:
            disks = []
            for j in i['disks']: disks.append(j['source'].split('/')[-1])
            result = {'name':i['name'],'zone':zone,'disks':disks}
            instances_fact.append(result)
    return instances_fact

def snapshot_instance_create(compute, project, zone, instance_name, disk, multiregion):
    snap_name = instance_name+'-'+disk+'-'+str(datetime.now().date())
    region = 'us' if multiregion else zone[:-2]
    snapshot_body = {"name": snap_name,"storageLocations": [ region ] }
    compute.disks().createSnapshot(project=project, zone=zone, disk=disk, body=snapshot_body).execute()
    return snap_name

def snapshot_get_status(compute, project, snapshot):
    result = compute.snapshots().get(project=project, snapshot=snapshot).execute()
    return result['status']

def snapshot_create(compute, project, instances, multiregion):
    debug("Affected instance: ")
    snap_list = []
    for i in instances:
        debug(i)
        for d in i['disks']:
            result = snapshot_instance_create(compute=compute, project=project, zone=i['zone'], instance_name=i['name'], disk=d, multiregion=multiregion)
            debug ("Taken snapshot with name: "+result)
            snap_list.append(result)
    return snap_list

def snapshot_list(compute, project):
    debug ("Snapshots found in project: "+project)
    snap_facts = []
    result = compute.snapshots().list(project=project).execute()
    if 'items' in result:
        for i in result['items']:
            temp = {'name':i['name'], 'zone':i['sourceDisk'].split('/')[-3], 'disk':i['sourceDisk'].split('/')[-1], 'created':i['creationTimestamp']}
            debug (temp)
            snap_facts.append(temp)
    return snap_facts

def snapshot_delete(compute,project,name):
    debug ("Snapshot "+name+" to be deleted")
    result = compute.snapshots().delete(project=project, snapshot=name).execute()
    debug (result)

def main():
    args = parse_args()
    global debug_status
    debug_status = args.debug
    time_now = datetime.now(timezone(timedelta(-1, 57600)))
    debug ("Current time: "+str(time_now))
    list_target_instances = args.instances.split(',')
    list_snap_ingnored = args.ignore.split(',')
    debug("Snapshots will be ignored: "+str(list_snap_ingnored) )

### Authenticate for google compute engine
    compute = google_compute_auth(args.key_file)

### Get of zones for region
    zones = list_zones_name(compute, args.project, args.region)

### Get of target instances list like a dict {'disks': [u''], 'name': u'', 'zone': u''}
    instances = []
    for i in zones:
        result = instances_get_fact(compute, args.project, i)
        for j in result: 
            if j['name'] in list_target_instances: instances.append(j)

### Create snapshots
    if args.action == 'create': 
        snap_list = snapshot_create(compute, args.project, instances, args.multiregion)    
        debug(snap_list)
### Waiting for snapshots are ready
        debug ("Waiting for snapshots are completed")
        for i in snap_list:
            for x in range(10):
                try: 
                    status = snapshot_get_status(compute, args.project, i)
                    break
                except:
                    debug ("Snapshot is not started")
                    time.sleep(1)
            while status != ('READY' or 'FAILED'):
                time.sleep(1)
                status = snapshot_get_status(compute, args.project, i)
            debug ('Status of '+i+' = '+status)

### Delete old snapshots
    if args.action == 'delete':
        snap_list = snapshot_list(compute, args.project)
        for i in instances:
            for disk in i['disks']:
                for snap in snap_list:
                    if disk == snap['disk'] and i['zone'] == snap['zone'] and (snap['name'] not in list_snap_ingnored): 
                        snap_time = datetime.strptime(snap['created'][:-3]+snap['created'][-2:], "%Y-%m-%dT%H:%M:%S.%f%z")
                        if (time_now - snap_time).days >= args.days : snapshot_delete (compute, args.project, snap['name']) 

if __name__ == "__main__":
        main()

