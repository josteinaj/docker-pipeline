# -*- coding: utf-8 -*-

import os
import sys
import re
from pprint import pprint
from slacker import Slacker
import yaml
from yaml.composer import Composer
from yaml.constructor import Constructor
import gettext
import docker
import hashlib

global config
global translation
global _
global slack
global docker_client
global docker_container_id

class Common:

    @staticmethod
    def init(path, docker_container):
        global config, translation, _, slack, docker_client, docker_container_id
        
        config = Common.load_yaml(path)
        
        translation = gettext.translation('messages', os.path.join(os.path.dirname(__file__), "i18n"), [Common.get_config("language", "en")])
        translation.install()
        
        docker_container_id = docker_container
        docker_client = docker.Client(base_url='unix://var/run/docker.sock')
        
        slack = {"slack": None, "channel": None, "botname": None}
        if os.path.exists("/mnt/config/slack.token"):
            with open("/mnt/config/slack.token", 'r') as f:
                slack_token = f.readline().rstrip()
            slack["slack"] = Slacker(slack_token)
            slack["botname"] = config.get("slack-botname", "docker-pipeline")
            slack["channel"] = config.get("slack-channel", "#test")
        else:
            pass # print(_("No slack token available, won't post to Slack"+": /mnt/config/slack.token"))

    @staticmethod
    def get_config(key, default):
        if config and key in config:
            return config[key]
        else:
            return default

    @staticmethod
    def message(msg):
        global slack
        if slack["slack"]:
            slack.chat.post_message(slack["channel"], msg, slack["botname"])
        else:
            print(msg)
            sys.stdout.flush()

    @staticmethod
    def list_files(directory, shallow=False):
        files = []
        if os.path.isdir(directory):
            for item in os.listdir(directory):
                item_fullpath = os.path.join(directory, item)
                if os.path.isfile(item_fullpath):
                    files.append(item_fullpath)
                elif os.path.isdir(item_fullpath):
                    if not shallow:
                        files.extend(list_files(item_fullpath))
        else:
            files.append(directory)
        return files

    @staticmethod
    def load_yaml(path):
        config = None
        if os.path.exists(path):
            try:
                with open(path, 'r') as file:
                    basename = os.path.basename(path)
                    loader = yaml.Loader(file.read())
                    def compose_node(parent, index):
                        # the line number where the previous token has ended (plus empty lines)
                        line = loader.line
                        column = loader.column
                        node = Composer.compose_node(loader, parent, index)
                        node.__line__ = line + 1
                        node.__column__ = column + 1
                        node.__basename__ = basename
                        node.__location__ = basename+":"+str(line + 1)
                        return node
                    def construct_mapping(node, deep=False):
                        mapping = Constructor.construct_mapping(loader, node, deep=deep)
                        mapping['__line__'] = node.__line__
                        mapping['__column__'] = node.__column__
                        mapping['__basename__'] = node.__basename__
                        mapping['__location__'] = node.__location__
                        return mapping
                    loader.compose_node = compose_node
                    loader.construct_mapping = construct_mapping
                    config = loader.get_single_data()
                    
            except (yaml.error.YAMLError, yaml.reader.ReaderError, yaml.scanner.ScannerError) as e:
                message(e)
            except (yaml.parser.ParserError, yaml.composer.ComposerError, yaml.constructor.ConstructorError) as e:
                message(e)
            except (yaml.emitter.EmitterError, yaml.serializer.SerializerError, yaml.representer.RepresenterError) as e:
                message(e)
        return config

    @staticmethod
    def docker_build(path):
        Common.message("Building docker image: "+path)
        response = [line for line in docker_client.build(path=path, rm=True, forcerm=True)]
        image_id = None
        for line in reversed(response):
            line_text = eval(line)['stream'].strip()
            if re.search(r'^Successfully built [^ ]+$', line_text):
                image_id = re.sub(r'^Successfully built ', '', line_text)
                break
        return image_id

    @staticmethod
    def docker_run(image, volumes, command=None):
        container_details = docker_client.inspect_container(docker_container_id)
        host_volumes = {}
        for volume in volumes:
            new_volume = Common.host_path(volume)
            if new_volume:
                host_volumes[new_volume] = volumes[volume]
        container = docker_client.create_container(image, host_config=docker_client.create_host_config(binds=host_volumes), command=command)
        docker_client.start(container=container)
        log_stream = docker_client.logs(container=container, stream=True)
        for line in log_stream:
            Common.message(line)
        docker_client.wait(container=container)
        docker_client.remove_container(container=container)

    @staticmethod
    def host_path(path):
        container_details = docker_client.inspect_container(docker_container_id)
        for mount in container_details['Mounts']:
            if 'Source' in mount and 'Destination' in mount and path.startswith(mount['Destination']):
                return mount['Source']+path[len(mount['Destination']):]
        return None

    @staticmethod
    def hashfile(path):
        with open(path, 'rb') as f:
            hasher = hashlib.sha256()
            blocksize = 65536
            buf = f.read(blocksize)
            while len(buf) > 0:
                hasher.update(buf)
                buf = f.read(blocksize)
            return hasher.digest()
        return None
    
    @staticmethod
    def first_line(path):
        for root, subdirs, files in os.walk(path):
            for file in files:
                with open(root+'/'+file, 'r') as f:
                    return f.readline().strip()
        return ""
    
    @staticmethod
    def write_file(path, text):
        with open(path, 'w') as f:
           f.write(text)
           f.close() 