# README

## Build, Run & Debug
Best is to build and debug your code inside of a docker container. The repository contains a 'docker-compose.yml' with all services needed. The 'docker-compose.dev.yml' is only to overcome an issue with the pyCharm editor.

In general you should use the 'cq-client'/'cq-win_client' for development whith linux/arm64 or linux/amd64. 

If you are using pyCharm you should select as interpreter:
* add interpreter: On Docker Compose...
* select the corresponding development service
  * arm64 : cq-client
  * amd64 : cq-win_client
* select as option 'System Interpreter'
* add a new path to:
  * arm64 : '/opt/anaconda/envs/cadquery/bin/python3'
  * amd64 : '/opt/conda/envs/cq/bin/python3'

You should edit your run configuration and select one of the file in the 'test' directory.

To show the generated shapes you must launch the *cq-server* service. You will then find here the ![cadquery_viewer](http://localhost:5050).

After this you are able to run and debug the code in your docker container.

## Folder Structure

* *test* Folder - scripts that build and test
* [*components* Folder](./components/Readme.md) - components that can be reused


