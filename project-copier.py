import requests
from copy import copy

import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--input', '-i', type=str, required=True, help='Input file path')
parser.add_argument('--output', '-o', type=str, required=True, help='Output file path')
args = parser.parse_args()

class ClusterData:
    def __init__(self, clusterId, tenant, url, app_name, secret_key) -> None:
        self.clusterId = clusterId
        self.tenant = tenant
        self.url = url
        self.app_name = app_name
        self.secret_key = secret_key
        self.getToken()
    
    def getToken(self):
        payload = f"grant_type=client_credentials&client_id={self.app_name}&client_secret={self.secret_key}"
        headers = { 'content-type': "application/x-www-form-urlencoded" }
        r = requests.post(f"{self.url}/auth/realms/{self.tenant}/protocol/openid-connect/token", payload, headers=headers)
        r.raise_for_status()

        self.token = r.json()["access_token"]
    
    def getProjects(self):
        headers = {'Authorization': 'Bearer ' + self.token}

        projects_r = requests.get(f"{self.url}/v1/k8s/clusters/{self.clusterId}/projects", headers=headers)
        projects_r.raise_for_status()
        return projects_r.json()
    
    def putProjects(self, projects):
        headers = {'Authorization': 'Bearer ' + self.token}

        for proj in projects:
            r = requests.post(f"{self.url}/v1/k8s/clusters/{self.clusterId}/projects", headers=headers, json=proj)
            r.raise_for_status()
    
    def getNodePools(self):
        headers = {'Authorization': 'Bearer ' + self.token}
        nodepools_r = requests.get(f"{self.url}/v1/k8s/clusters/{self.clusterId}/node-pools", headers=headers)
        nodepools_r.raise_for_status()
        return nodepools_r.json()


input_cluster = ClusterData("255660e0-b6ac-4ebe-9208-7442b18f7102", "vaquitat", "https://test.run.ai", "omric", "skbBVZF3PTsTMrcVw3IbDdRqAiK5Eclo")
output_cluster = ClusterData("750acc35-44ed-411a-bfab-196efde4d5a7", "vaquitat", "https://test.run.ai", "omric", "skbBVZF3PTsTMrcVw3IbDdRqAiK5Eclo")

projects = input_cluster.getProjects()
input_nodepools = input_cluster.getNodePools()
output_nodepools = output_cluster.getNodePools()

input_nodepool_names = [x['name'] for x in input_nodepools].sort()
output_nodepool_names = [x['name'] for x in output_nodepools].sort()
if input_nodepool_names != output_nodepool_names:
    print(f"Mismatch in clusters nodepools! input cluster nodepools: {input_nodepool_names}, output cluster nodepools: {output_nodepool_names}")
    raise ValueError

nodepool_mapping = {}
for i in input_nodepools:
    matching_nodepool = None
    for j in output_nodepools:
        if j['name'] == i['name']:
            matching_nodepool = j
    if matching_nodepool == None:
        print(f"Error finding matching nodepool for {i['name']}")
    nodepool_mapping[i['id']] = matching_nodepool['id']

new_projects = []
for proj in projects:
    new_proj = copy(proj)
    new_proj['nodePoolsResources'] = []
    for npr in proj['nodePoolsResources']:
        new_npr = copy(npr)
        new_npr['nodePool']['id'] = nodepool_mapping[new_npr['nodePool']['id']]
        del new_npr['cpu'] 
        del new_npr['memory'] 
        new_proj['nodePoolsResources'].append(new_npr)
    
    del new_proj['resources']['cpu']
    del new_proj['resources']['memory']

    new_projects.append(new_proj)

output_cluster.putProjects(new_projects)