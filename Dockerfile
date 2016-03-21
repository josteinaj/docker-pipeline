FROM ubuntu:15.10

MAINTAINER Jostein Austvik Jacobsen

# Set working directory to home directory
WORKDIR /root/

# Set up repositories
RUN apt-get update && apt-get install -y software-properties-common
RUN sed -i.bak 's/main$/main universe/' /etc/apt/sources.list

# Set locale
RUN locale-gen en_GB en_GB.UTF-8
ENV LANG C.UTF-8
ENV LANGUAGE en_GB:en
ENV LC_ALL C.UTF-8

# Install dependencies
RUN apt-get update && apt-get install -y wget unzip curl vim
RUN apt-get update && apt-get install -y python3-pip python3-yaml
RUN apt-get update && apt-get install -y apt-transport-https ca-certificates
RUN pip3 install slacker docker-py

VOLUME ["/tmp"]

COPY src /root

ENTRYPOINT ["/root/run.sh"]
