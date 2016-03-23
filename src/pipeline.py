# -*- coding: utf-8 -*-

import os
import tempfile
from pprint import pprint
from common import Common
import mimetypes
import difflib

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
        self.steps = []
        self.tests = {}
        for step in self.config['pipeline']:
            if isinstance(step, dict):
                if 'dockerfile' in step:
                    image_id = Common.docker_build(os.path.dirname(path)+"/"+step['dockerfile']+"/")
                    self.steps.append({'image':{'name':step['dockerfile'], 'id':image_id}})
                elif 'test' in step:
                    if not step['test'] in self.tests:
                        self.tests[step['test']] = {}
                    self.tests[step['test']][len(self.steps)] = step
                    step['name'] = step['test']
                    self.steps.append({'test':step})
                else:
                    Common.message("WARNING: unknown step type: dictionary with key '"+list(step.keys())[0]+"' (skipping!)")
            else:
                self.steps.append({'image':{'name':step, 'id':step}})

    def run(self, config_path, input_path, output_path, status_path, test=None):
        temp_path = tempfile.mkdtemp(prefix='pipeline-')
        
        success = True
        
        current_input_path = None
        current_output_path = None
        current_status_path = None
        position = 0
        for step_object in self.steps:
            step_type = list(step_object.keys())[0]
            step = step_object[step_type]
            
            if step_type == 'image':
                Common.message(self.id+str(position)+' -- Running image: '+step['name'])
                
                if position > 0:
                    current_input_path = current_output_path
                else:
                    current_input_path = input_path
                
                if position < len(self.steps) - 1:
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
                volumes[current_input_path] =  { 'bind': '/mnt/input', 'mode': 'ro' }
                volumes[current_output_path] = { 'bind': '/mnt/output', 'mode': 'rw' }
                volumes[current_status_path] = { 'bind': '/mnt/status', 'mode': 'rw' }
                
                Common.docker_run(step['id'], volumes)
                position += 1
            
            elif step_type == 'test':
                if step['name'] == test:
                    Common.message('   -- Evaluating test')
                    if 'expect' in step:
                        expected_files = {}
                        actual_files = {}
                        actual_path = current_output_path if current_output_path else input_path
                        expected_path = os.path.dirname(self.path)+"/tests/"+step['expect']
                        
                        for root, subdirs, files in os.walk(actual_path):
                            for file in files:
                                actual_files[os.path.relpath(root, actual_path)+'/'+file] = {'hash': Common.hashfile(root+'/'+file),
                                                                                             'fullpath': root+'/'+file }
                        for root, subdirs, files in os.walk(expected_path):
                            for file in files:
                                expected_files[os.path.relpath(root, expected_path)+'/'+file] = {'hash': Common.hashfile(root+'/'+file),
                                                                                                 'fullpath': root+'/'+file }
                        
                        for file in actual_files:
                            if not file in expected_files:
                                Common.message("FAILED: file should not be present in output: "+file)
                                success = False
                            elif expected_files[file]['hash'] != actual_files[file]['hash']:
                                Common.message("FAILED: content in actual and expected files differ: "+file)
                                success = False
                                mime = mimetypes.guess_type(file)
                                if mime[0].startswith('text/') and os.stat(actual_files[file]['fullpath']).st_size < 1000000 and os.stat(expected_files[file]['fullpath']).st_size < 1000000:
                                    with open(expected_files[file]['fullpath'], 'r') as expected_file:
                                        with open(actual_files[file]['fullpath'], 'r') as actual_file:
                                            expected_lines = expected_file.readlines()
                                            actual_lines = actual_file.readlines()
                                            max_lines = 30
                                            for diffline in difflib.unified_diff(expected_lines, actual_lines, fromfile=file, tofile=file):
                                                Common.message(diffline.strip())
                                                max_lines -= 1
                                                if max_lines <= 0:
                                                    break
                        for file in expected_files:
                            if not file in actual_files:
                                Common.message("FAILED: file should be present in output: "+file)
                                success = False
                    
                    if 'status' in step:
                        actual_status = None
                        for root, subdirs, files in os.walk(current_status_path):
                            for file in files:
                                with open(root+'/'+file, 'r') as f:
                                    actual_status = f.readline().strip()
                                    break
                            if actual_status:
                                break
                        if actual_status != step['status']:
                            Common.message("FAILED: actual status and expected status differ: \n  expected: "+step['status']+"\n    actual: "+actual_status)
                            success = False
                    
        return success    
    
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
            
            self.run(config_path, input_path, output_path, status_path, test=test_name)
            
            Common.message("\n"+_('Host system path to pipeline output is:')+' '+Common.host_path(os.path.dirname(output_path)))

    def dump(self):
        #pprint(self.config)
        #pprint(self.steps)
        #pprint(self.tests)
        pass
