import os
import sys
import requests
import yaml

def generate_yaml(project_name, repo_url):
    repository_yaml = {
        'apiVersion': 'v1',
        'kind': 'Secret',
        'metadata': {
            'name': f'repository-{project_name}',
            'namespace': 'argocd',
            'labels': {
                'argocd.argoproj.io/secret-type': 'repository'
            }
        },
        'stringData': {
            'username': 'argocd',
            'password': '${argo_password_rd}',
            'project': '${group_name}',
            'type': 'git',
            'url': repo_url
        },
        'type': 'Opaque'
    }

    application_yaml = {
        'apiVersion': 'argoproj.io/v1alpha1',
        'kind': 'Application',
        'metadata': {
            'name': project_name,
            'namespace': 'argocd'
        },
        'spec': {
            'project': '${group_name}',
            'source': {
                'path': 'overlays/dev',
                'repoURL': repo_url,
                'targetRevision': 'HEAD'
            },
            'destination': {
                'server': 'https://kubernetes.default.svc',
                'namespace': '${group_name}-dev'
            },
            'ignoreDifferences': [
                {
                    'group': 'apps',
                    'kind': 'Rollout',
                    'jsonPointers': [
                        '/spec/replicas'
                    ]
                },
                {
                    'group': '*',
                    'kind': '*'
                }
            ],
            'revisionHistoryLimit': 10
        }
    }

    with open(f'repository_template_{project_name}.yaml', 'w') as repo_file:
        yaml.dump(repository_yaml, repo_file)

    with open(f'application_template_{project_name}.yaml', 'w') as app_file:
        yaml.dump(application_yaml, app_file)

def generate_project_template(group_name):
    project_yaml = {
        'apiVersion': 'argoproj.io/v1alpha1',
        'kind': 'AppProject',
        'metadata': {
            'name': group_name,
            'namespace': 'argocd'
        },
        'spec': {
            'clusterResourceWhitelist': [
                {
                    'group': '*',
                    'kind': '*'
                }
            ],
            'description': f'{group_name} apps',
            'destinations': [
                {
                    'name': '*',
                    'namespace': '*',
                    'server': '*'
                }
            ],
            'namespaceResourceWhitelist': [
                {
                    'group': '*',
                    'kind': '*'
                }
            ],
            'sourceRepos': ['*']
        }
    }

    with open('project_template.yaml', 'w') as project_file:
        yaml.dump(project_yaml, project_file)

if __name__ == '__main__':
    api_token = os.environ.get('ARGO_API')
    group_path = 'raiadrogasil/rd/devops-rd/argocd/${group_name}'
    headers = {'PRIVATE-TOKEN': api_token}

    # Get the group ID
    group_url = f'https://gitlab.com/api/v4/groups/{group_path.replace("/", "%2F")}'
    group_response = requests.get(group_url, headers=headers).json()
    group_id = group_response['id']

    # Get the projects in the group
    projects_url = f'https://gitlab.com/api/v4/groups/{group_id}/projects?per_page=100'
    projects_response = requests.get(projects_url, headers=headers).json()

    for project in projects_response:
        project_name = project['name']
        repo_url = project['http_url_to_repo']
        generate_yaml(project_name, repo_url)

    generate_project_template('${group_name}')
