Snapshot operation in GCP

**Requirements:**
- python 3.5 or older
- google-api-python-client (pip3 install google-api-python-client)

**Execution:**
```
python3 gcp_snap.py  --help
usage: gcp_snap.py [-h] --project PROJECT --region REGION --key-file KEY_FILE
                   [-d DAYS] [--ignore IGNORE] [--multiregion] [--debug]
                   instances {create,delete}

Taking snapshort of GCP instances

positional arguments:
  instances             List of instances comma separated
  {create,delete}       Action for snapshort: create or delete

optional arguments:
  -h, --help            show this help message and exit
  --project PROJECT     Project name
  --region REGION       Region name
  --key-file KEY_FILE   Path to service account json file
  -d DAYS, --days DAYS  How old days snapshot should be deleted for instances,
                        0 - for every snapshots; default 7
  --ignore IGNORE       List of snapshots name, what should not be deleted
  --multiregion         Location store for snapshot will be multiregion
  --debug               Debug information to stdout
```
**Example:**  
```
./gcp_snap.py test2,test3,test4 create --project devops-test-219812 --region us-central1 --key-file ansible-sa.json --multiregion
./gcp_snap.py test2,test3,test4 delete --project devops-test-219812 --region us-central1 --key-file ansible-sa.json --ignore test2-manual,test3-snap --days 0
```