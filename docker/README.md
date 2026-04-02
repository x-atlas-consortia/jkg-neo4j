# JSON Knowledge Graph (JKG) 
# Docker/neo4j Deployment of JKG

Files in this directory create Docker images used to build a Docker container running an instance
of neo4j Community Edition that contains a knowledge graph imported from
a JSON file in JSON Knowledge Graph (JKG) format.

Docker images supporting both linux/amd64 (x86-64) and linux/arm64 platforms are available. 

## Requirements
  - [Docker must be installed](https://docs.docker.com/engine/install/) on the development machine with Docker BuildX build support.  By default, Docker BuildX support is installed with Docker Desktop.  If you have a version of Docker installed without Desktop you can [install Docker BuildX manually](https://docs.docker.com/build/install-buildx/).
  - The Bash shell scripts contained in this directory are intended for use on Mac OS X or Linux.  These scripts will not work on Windows. (The resulting Docker images will, however, run on Windows.)

## Build Scripts
#### build-push-multi-arch.sh

**build-push-multi-arch.sh** script is a Bash script which will build and push to DockerHub the JKG Neo4j Docker images with support for both x86-64 (ARM 64-bit) and amd64 (AMD 64-bit) platforms. 
The script takes advantage of the Docker Buildx `build --platform` option to create the multi-platform images.

Before running this script first log into DockerHub with the `docker login` command using an account that has write privileges in the HuBMAP DockerHub Organization.

usage: ./build-push-multi-arch.sh [-rv version]
If run without the `-rv` option the script will build the multi-platform images and push them to DockerHub with the tag `hubmap/jkg-neo4j:latest`.
If given the `-rv <version` argument the script will build the multi-platrom images and push them to DockerHub with the addional tags of `hubmap/jkg-neo4j:current-release` and `hubmap/jkg-neo4j:<version>`, where <versions> is replaced with the version entered as the version argument.

e.g. `./build-push-multi-arch.sh -rv 3.2.4`

#### build-local.sh
usage: ./build-local.sh

The build-local.sh builds a local image for use during development and debugging of the JKG Neo4j Docker container. The locally built image will be tagged as `jkg-neo4j-local`  To run the local image use the [run.sh]() script at the top level directory in this repository with the arguments `-t local`.

## Files used for image build
| File                  | Description                                                                                                              | Scope          |
|-----------------------|--------------------------------------------------------------------------------------------------------------------------|----------------|
| **Dockerfile**        | Instructions for building the container                                                                                  | Build file     |
| **neo4j.conf**        | Configuration file for the neo4j instance                                                                                | Added to image |
| **neo4j.conf.noauth** | Version of configuration file used for operations that require disabling authentication                                  | Added to image |
| **apoc.conf**         | Custom APOC configuration that enables imports into neo4j from the file system and exports from neo4j to the file system | added to image |
| **start.sh**          | Script that configures the neo4j database per parameters                                                                 | Added to image |

## Support Scripts
| File                         | Description                                                                                                     |
|------------------------------|-----------------------------------------------------------------------------------------------------------------|
| **build-local.sh**           | Builds the Docker image locally (not pushed to DockerHub).  The image is built and tagged as `jkg-neo4j-local`. |
| **build-push-multi-arch.sh** | Builds images for x86-64 and arm64 platforms and pushes the images to DockerHub.                                |

