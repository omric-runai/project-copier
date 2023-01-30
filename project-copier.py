import requests
from copy import copy
import logging

requests.urllib3.disable_warnings()

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
        r = requests.post(f"{self.url}/auth/realms/{self.tenant}/protocol/openid-connect/token", payload, headers=headers, verify=False)
        r.raise_for_status()

        self.token = r.json()["access_token"]
    
    def getProjects(self):
        headers = {'Authorization': 'Bearer ' + self.token}

        projects_r = requests.get(f"{self.url}/v1/k8s/clusters/{self.clusterId}/projects", headers=headers, verify=False)
        projects_r.raise_for_status()
        return projects_r.json()
    
    def getDepartments(self):
        headers = {'Authorization': 'Bearer ' + self.token}

        projects_r = requests.get(f"{self.url}/v1/k8s/clusters/{self.clusterId}/departments", headers=headers, verify=False)
        projects_r.raise_for_status()
        return projects_r.json()
    
    def putProjects(self, projects):
        headers = {'Authorization': 'Bearer ' + self.token}
        
        print(f'Updating {len(projects)} projects to new backend...')
        cnt = 1
        for proj in projects:
            print(f'Updating proj {proj["name"]}, {cnt}/{len(projects)} ...')

            r = requests.post(f"{self.url}/v1/k8s/clusters/{self.clusterId}/projects", headers=headers, json=proj, verify=False)
            r.raise_for_status()
            cnt += 1
    
    def getNodePools(self):
        headers = {'Authorization': 'Bearer ' + self.token}
        nodepools_r = requests.get(f"{self.url}/v1/k8s/clusters/{self.clusterId}/node-pools", headers=headers, verify=False)
        nodepools_r.raise_for_status()
        return nodepools_r.json()


input_cluster = ClusterData("b957075b-5000-4952-a1d4-67cfa9e433c8", "runai", "https://omric-2-1.runailabs.com", "omric", "5831cfb9-129b-4304-9af2-3a2c41df3b31")
output_cluster = ClusterData("5500528c-c593-4e4c-93a5-a2e58345af24", "runai", "https://omric-2-8.runailabs.com", "omric", "e80346f6-90cd-4ef5-ba77-effba090ec63")

print("Getting input projects...")
projects = input_cluster.getProjects()

print("Getting output nodepools...")
nodepools = output_cluster.getNodePools()

print("Getting output department...")
departments = output_cluster.getDepartments()

print(f'Updating {len(projects)} to new scheme...')
new_projects = []
cnt = 1
for proj in projects:
    print(f'Updating project {proj["name"]}, {cnt}/{len(projects)}')
    new_proj = copy(proj)
    new_proj['clusterUuid'] = output_cluster.clusterId
    new_proj['tenantId'] = nodepools[0]['tenantId']
    new_proj['departmentId'] = departments[0]['id']
    new_proj['interactiveJobTimeLimitSecs'] = "Null"
    new_proj['resources'] = {
        "gpu": {
            "deserved": proj['deservedGpus'],
            "overQuotaWeight": proj['gpuOverQuotaWeight'],
            "maxAllowed": proj['maxAllowedGpus']
        },
        "cpu": {
            "overQuotaWeight": proj['gpuOverQuotaWeight'],
            "maxAllowed": proj['maxAllowedGpus']
        },
        "memory": {
            "overQuotaWeight": proj['gpuOverQuotaWeight'],
            "maxAllowed": proj['maxAllowedGpus']
        }
    }
    new_proj['nodePoolsResources'] = [{
        'id': 1,
        'nodePool': {
            'id': nodepools[0]['id'],
            'name': nodepools[0]['name']
        },
        "gpu": {
            "deserved": proj['deservedGpus'],
            "overQuotaWeight": proj['gpuOverQuotaWeight'],
            "maxAllowed": proj['maxAllowedGpus']
        },
        "cpu": {
            "overQuotaWeight": 1,
            "maxAllowed": proj['maxAllowedGpus']
        },
        "memory": {
            "overQuotaWeight": 1,
            "maxAllowed": proj['maxAllowedGpus']
        }
    }]

    del new_proj['interactiveJobTimeLimitSecs']

    new_projects.append(new_proj)
    cnt += 1

print("Posting projects to new backend...")
output_cluster.putProjects(new_projects)