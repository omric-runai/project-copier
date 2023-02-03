import requests
from copy import copy
import configparser

requests.urllib3.disable_warnings()

config = configparser.ConfigParser()
config.read('config.ini')

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

input_cluster_id = config['INPUT']['clusterId']
input_tenant_name = config['INPUT']['tenantName']
input_cluster_url = config['INPUT']['clusterUrl']
input_app_name = config['INPUT']['appName']
input_app_secret = config['INPUT']['secret']

output_cluster_id = config['OUTPUT']['clusterId']
output_tenant_name = config['OUTPUT']['tenantName']
output_cluster_url = config['OUTPUT']['clusterUrl']
output_app_name = config['OUTPUT']['appName']
output_app_secret = config['OUTPUT']['secret']


input_cluster = ClusterData(input_cluster_id, input_tenant_name, input_cluster_url, input_app_name, input_app_secret)
output_cluster = ClusterData(output_cluster_id, output_tenant_name, output_cluster_url, output_app_name, output_app_secret)



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