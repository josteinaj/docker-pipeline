FROM ubuntu:15.10

MAINTAINER Jostein Austvik Jacobsen

# Set working directory to home directory
WORKDIR /root/

# Set up repositories
RUN apt-get install -y software-properties-common
RUN sed -i.bak 's/main$/main universe/' /etc/apt/sources.list

# Set locale
RUN locale-gen en_GB en_GB.UTF-8
ENV LANG C.UTF-8
ENV LANGUAGE en_GB:en
ENV LC_ALL C.UTF-8

# Install dependencies
RUN apt-get update && apt-get install -y wget unzip curl vim
RUN apt-get update && apt-get install -y python3-pip python3-yaml
RUN pip3 install mutagen slacker

COPY src /root

CMD if [ -e /tmp/script/run.sh ]; then /tmp/script/run.sh ; else echo "Script missing: /tmp /script/run.sh" ; fi
