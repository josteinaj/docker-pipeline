# -*- coding: utf-8 -*-

import os
import tempfile
from pprint import pprint
from common import Common

class Pipeline:
    
    def __init__(self, path, host_path, subpipeline=None, subpipeline_id='!'):
        self.path = path
        self.host_path = host_path
        Common.message("host_path: "+host_path)
        if subpipeline:
            self.config = subpipeline
        else:
            self.config = Common.load_yaml(path)
        self.id = subpipeline_id
        self.images = []
        self.tests = {}
        for image in self.config['pipeline']:
            if isinstance(image, dict):
                if 'dockerfile' in image:
                    image_id = Common.docker_build(os.path.dirname(path)+"/"+image['dockerfile']+"/")
                    self.images.append(image_id)
                elif 'test' in image:
                    if not image['test'] in self.tests:
                        self.tests[image['test']] = {}
                    self.tests[image['test']][len(self.images)] = image
                else:
                    Common.message("WARNING: unknown step type: dictionary with key '"+list(image.keys())[0]+"' (skipping!)")
            else:
                self.images.append(image)

    def run(self, config_path, input_path, output_path, status_path):
        temp_path = tempfile.mkdtemp(prefix='pipeline-')
        
        current_input_path = None
        current_output_path = None
        current_status_path = None
        for position, image in enumerate(self.images):
            Common.message(self.id+str(position)+" -- Running "+image)
            
            if position > 0:
                current_input_path = current_output_path
            else:
                current_input_path = input_path
            
            if position < len(self.images) - 1:
                current_output_path = temp_path+"/"+str(position)+"/output"
                current_status_path = temp_path+"/"+str(position)+"/status"
                os.makedirs(current_output_path)
                os.makedirs(current_status_path)
            else:
                current_output_path = output_path
                current_status_path = status_path
            
            volumes = {}
            if config_path:
                volumes[config_path] = { 'bind': '/mnt/config', 'mode': 'ro' }
                #Common.message("Mounting "+str(config_path)+" as "+str(volumes[config_path]['bind']))
            volumes[current_input_path] =  { 'bind': '/mnt/input', 'mode': 'ro' }
            #Common.message("Mounting "+str(current_input_path)+" as "+str(volumes[current_input_path]['bind']))
            volumes[current_output_path] = { 'bind': '/mnt/output', 'mode': 'rw' }
            #Common.message("Mounting "+str(current_output_path)+" as "+str(volumes[current_output_path]['bind']))
            volumes[current_status_path] = { 'bind': '/mnt/status', 'mode': 'rw' }
            #Common.message("Mounting "+str(current_status_path)+" as "+str(volumes[current_status_path]['bind']))
            
            Common.docker_run(image, volumes)
    
    def run_tests(self):
        for test_name in self.tests:
            Common.message("\n---\n"+_('Running test:')+' '+test_name+"\n")
            
            test = self.tests[test_name]
            
            temp_path = tempfile.mkdtemp(prefix='test-')
            tests_path = os.path.dirname(self.path)+"/tests"
            
            config_path = None # tests_path+"/"+test_name+"/config"
            input_path = tests_path+"/"+test_name
            output_path = temp_path+"/"+test_name+"/output"
            status_path = temp_path+"/"+test_name+"/status"
            
            self.run(config_path, input_path, output_path, status_path)
            
            Common.message(_('Host system path to pipeline output is:')+' '+Common.host_path(os.path.dirname(output_path)))
            
            expected_files = []
            actual_files = []
            for root, subdirs, files in os.walk(output_path):
                #pprint([root, subdirs, files])
                #Common.message("TODO: compare output_path with test.expected")
                pass
            #Common.message("TODO: compare status_path with test.status")

    def dump(self):
        #pprint(self.config)
        #pprint(self.images)
        #pprint(self.tests)
        pass
