**gitlab-ci:**

```
stages:
  - build
  - deploy
```

Define as etapas do pipeline como "build" e "deploy".

```
build:
  stage: build
  image: harbor.rd.com.br/devops/kubectl:2.0.0
  script:
    - export CI_PROJECT_PATH=$(echo $CI_PROJECT_PATH | awk -F'/' '{print $3}')
```
- Define a etapa "build" do pipeline.
- Especifica a etapa como "build" e define a imagem Docker a ser usada como harbor.rd.com.br/devops/kubectl:2.0.0.
- A partir desta linha, começa a seção script, que contém os comandos a serem executados nesta etapa.
- A linha acima extrai o terceiro campo do valor de CI_PROJECT_PATH usando o comando awk e o armazena na variável CI_PROJECT_PATH.

`- sed -e "s/\${group_name}/${CI_PROJECT_PATH}/g" generate_yaml.py > generate_yaml_modified.py`

- Executa um comando de substituição usando sed no arquivo generate_yaml.py.
- Substitui todas as ocorrências de ${group_name} pelo valor de CI_PROJECT_PATH.
- Redireciona a saída para um novo arquivo chamado generate_yaml_modified.py.

```
    - pip install requests
    - pip install pyyaml
```

- Instala as dependências do Python requests e pyyaml usando o gerenciador de pacotes pip.

```
    - |
      group_url="https://gitlab.com/api/v4/groups/raiadrogasil%2Frd%2Fdevops-rd%2Fargocd%2F$CI_PROJECT_PATH"
      echo $group_url
      group_response=$(curl --header "PRIVATE-TOKEN: $ARGO_API" $group_url)
      group_id=$(echo $group_response | jq -r '.id')
      projects=$(curl --header "PRIVATE-TOKEN: $ARGO_API" "https://gitlab.com/api/v4/groups/$group_id/projects?per_page=100" | jq -r '.[].path')
      for project in $projects; do
        python generate_yaml_modified.py $project
      done
```
- Define uma variável group_url com a URL da API do GitLab, substituindo $CI_PROJECT_PATH no caminho.
- Exibe a URL no console.
- Faz uma solicitação à API do GitLab para obter a resposta e armazena-a na variável group_response.
- Extrai o ID do grupo da resposta usando o utilitário jq e armazena-o na variável group_id.
- Faz uma solicitação à API do GitLab para obter a lista de projetos no grupo e armazena-a na variável projects.
- Itera sobre cada projeto na lista e chama o script Python generate_yaml_modified.py, passando o nome do projeto como argumento.

```
  artifacts:
    paths:
      - 'repository_template_*.yaml'
      - 'application_template_*.yaml'
      - 'project_template.yaml'
```

- Define os artefatos a serem salvos após a conclusão da etapa "build".
- Os arquivos correspondentes aos padrões repository_template_*.yaml, application_template_*.yaml e project_template.yaml serão salvos como artefatos.

```
  tags:
    - docker
  only:
    - financial-dev
```
- Define as tags de execução para os jobs neste estágio como "docker".
- Especifica que este job será executado apenas para a branch "financial-dev".


**Python**

```
import os
import sys
import requests
import yaml
```
- Importa os módulos necessários: os, sys, requests e yaml.

```
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
            'password': 'glpat-yt61dXNX6s3F_6Pji7Tp',
            'project': '${group_name}',
            'type': 'git',
            'url': repo_url
        },
        'type': 'Opaque'
    }
```
- Define uma função chamada generate_yaml que recebe dois argumentos: project_name e repo_url.
- Cria um dicionário repository_yaml que representa o conteúdo do arquivo YAML a ser gerado.
- O dicionário contém informações como a versão da API, o tipo de recurso, metadados, dados de string e tipo.

```
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
```
- Cria um dicionário application_yaml que representa o conteúdo do arquivo YAML de aplicação a ser gerado.
- O dicionário contém informações como a versão da API, o tipo de recurso, metadados, especificações e configurações relacionadas ao aplicativo.

```
    with open(f'repository_template_{project_name}.yaml', 'w') as repo_file:
        yaml.dump(repository_yaml, repo_file)

    with open(f'application_template_{project_name}.yaml', 'w') as app_file:
        yaml.dump(application_yaml, app_file)
```
- Abre arquivos YAML com nomes baseados no project_name e escreve os dicionários repository_yaml e application_yaml nesses arquivos usando a função yaml.dump().

```
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
```
- Define uma função chamada generate_project_template que recebe um argumento group_name.
- Cria um dicionário project_yaml que representa o conteúdo do arquivo YAML do projeto a ser gerado.
- O dicionário contém informações como a versão da API, o tipo de recurso, metadados, especificações e configurações relacionadas ao projeto.

```
    with open('project_template.yaml', 'w') as project_file:
        yaml.dump(project_yaml, project_file)
```
- Abre um arquivo YAML chamado project_template.yaml e escreve o dicionário project_yaml nesse arquivo usando a função yaml.dump().

```
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
```

- Verifica se o script está sendo executado como o programa principal.
- Obtém o token de API do ambiente e o caminho do grupo.
- Cria um cabeçalho HTTP contendo o token de API.
- Faz uma solicitação GET para obter o ID do grupo usando a URL da API do GitLab.
- Faz uma solicitação GET para obter os projetos no grupo usando a URL da API do GitLab.
- Itera sobre a lista de projetos e para cada projeto, obtém o nome e a URL do repositório.
- Chama a função generate_yaml passando o nome do projeto e a URL do repositório.
- Chama a função generate_project_template passando o nome do grupo.
