# -*- coding: utf-8 -*-

import os
import tempfile
from pprint import pprint
from common import Common
import mimetypes
import difflib
import shutil

class Pipeline:
    
    def __init__(self, path, host_path, pipeline=None):
        self.path = path
        self.host_path = host_path
        if pipeline:
            self.pipeline = pipeline
        else:
            Common.message("host_path: "+host_path)
            self.pipeline = Common.load_yaml(path)
        self.steps = []
        self.tests = {}
        for step in self.pipeline['pipeline']:
            if isinstance(step, dict):
                if 'dockerfile' in step:
                    image_id = Common.docker_build(os.path.dirname(path)+"/"+step['dockerfile']+"/")
                    self.steps.append({'image':{'name':step['dockerfile'], 'id':image_id}})
                    
                elif 'unfold' in step:
                    self.steps.append({'unfold':{'name':'unfold', 'depth':step['unfold']}})
                
                elif 'test' in step:
                    if not 'input' in step['test']:
                        step['test']['input'] = '*'
                    test_input = step['test']['input']
                    
                    if not test_input in self.tests:
                        self.tests[test_input] = {}
                    self.tests[test_input][str(len(self.steps))] = step['test']
                    step['test']['name'] = test_input
                    self.steps.append(step)
                
                elif 'assert' in step:
                    assertion = { 'test': { 'name': '*', 'input': '*', 'status': step['assert'] }}
                    if not '*' in self.tests:
                        self.tests['*'] = {}
                    self.tests['*'][str(len(self.steps))] = assertion['test']
                    self.steps.append(assertion)
                
                elif 'foreach' in step:
                    subpipeline_name = 'pipeline' if not 'name' in self.pipeline['pipeline'] else self.pipeline['pipeline']['name']
                    subpipeline = Pipeline(
                                               self.path,
                                               self.host_path,
                                               pipeline={
                                                   'name': subpipeline_name,
                                                   'pipeline': step['foreach']
                                               }
                                           )
                    for test_input in subpipeline.tests:
                        if not test_input in self.tests:
                            self.tests[test_input] = {}
                        for subtest_id in subpipeline.tests[test_input]:
                            self.tests[test_input][str(len(self.steps))+'.'+subtest_id] = subpipeline.tests[test_input][subtest_id]
                    self.steps.append({ 'foreach': { 'name': subpipeline_name, 'pipeline': subpipeline }})
                
                else:
                    Common.message("WARNING: unknown step type: dictionary with key '"+list(step.keys())[0]+"' (skipping!)")
            else:
                self.steps.append({ 'image': { 'name': step, 'id': step }})

    def run(self, config_path, input_path, output_path, status_path, test=None, step_id='', step_depth=0):
        temp_path = tempfile.mkdtemp(prefix='pipeline-')
        
        tests_run = 0
        tests_failed = 0
        tests_skipped = 0
        
        pipeline_context_name = os.path.basename(input_path)
        padding = "".ljust(10+step_depth*2)
        Common.message(padding+'-- Context is: '+pipeline_context_name)
        
        current_input_path = None
        current_output_path = None
        current_status_path = None
        position = 0
        step_count = len([ step_object for step_object in self.steps if (list(step_object.keys())[0] != 'test' and list(step_object.keys())[0] != 'assert') ])
        for step_object in self.steps:
            step_type = list(step_object.keys())[0]
            step = step_object[step_type]
            
            if step_type != 'test' and step_type != 'assert':
                current_step_id = step_id+'/'+str(position)
                Common.message(current_step_id.ljust(10+step_depth*2)+'-- Running '+step_type+': '+step['name'])
                
                if position > 0:
                    current_input_path = current_output_path
                else:
                    current_input_path = input_path
                
                if position < step_count - 1:
                    current_output_path = temp_path+"/"+str(position)+"/output"
                    current_status_path = temp_path+"/"+str(position)+"/status"
                    os.makedirs(current_output_path)
                    os.makedirs(current_status_path)
                else:
                    current_output_path = output_path
                    current_status_path = status_path
                
                if step_type == 'image':
                    volumes = {}
                    if config_path:
                        volumes[config_path] = { 'bind': '/mnt/config', 'mode': 'ro' }
                    volumes[current_input_path] = { 'bind': '/mnt/input'+('/'+pipeline_context_name if not os.path.isdir(current_input_path) else ''), 'mode': 'ro' }
                    volumes[current_output_path] = { 'bind': '/mnt/output', 'mode': 'rw' }
                    volumes[current_status_path] = { 'bind': '/mnt/status', 'mode': 'rw' }
                    
                    Common.docker_run(step['id'], volumes)
                
                elif step_type == 'foreach':
                    for file_or_dir in Common.list_files(current_input_path):
                        result = step['pipeline'].run(config_path, file_or_dir, current_output_path+'/'+os.path.basename(file_or_dir), current_status_path, test=test, step_id=current_step_id, step_depth=step_depth+1)
                        tests_skipped += result['tests']['skipped']
                        tests_run += result['tests']['run']
                        tests_failed += result['tests']['failed']
                
                elif step_type == 'unfold':
                    prev_paths = []
                    paths = [ current_input_path ]
                    depth = step['depth']
                    while depth >= 0:
                        depth -= 1
                        prev_paths = list(paths)
                        paths = []
                        for current_path in prev_paths:
                            if not os.path.isdir(current_path):
                                continue
                            for item in os.listdir(current_path):
                                paths.append(os.path.join(current_path, item))
                    for path in paths:
                        if os.path.exists(current_output_path+'/'+os.path.basename(path)):
                            Common.message(padding+"   WARNING: file naming collision when unfolding: "+os.path.basename(path))
                            continue
                        if os.path.isdir(path):
                            shutil.copytree(path, current_output_path+'/'+os.path.basename(path))
                        else:
                            shutil.copy2(path, current_output_path+'/'+os.path.basename(path))

                else:
                    Common.message(padding+"   ERROR: could not process step type: "+step_type)
                    current_output_path = current_input_path
                
                position += 1
            
            else:
                if step['name'] == test or test == '*' or step['name'] == '*':
                    if 'context' in step and not step['context'] == pipeline_context_name:
                        continue
                    
                    success = True
                    
                    Common.message(padding+'-- Evaluating test: '+step['name'])
                    if 'expect' in step:
                        tests_run += 1
                        expected_files = {}
                        actual_files = {}
                        actual_path = current_output_path if current_output_path else input_path
                        expected_path = os.path.dirname(self.path)+"/tests/"+step['expect']
                        
                        if os.path.isdir(actual_path):
                            for root, subdirs, files in os.walk(actual_path):
                                for file in files:
                                    actual_files[os.path.relpath(root, actual_path)+'/'+file] = {'hash': Common.hashfile(root+'/'+file),
                                                                                                 'fullpath': root+'/'+file }
                        else:
                            actual_files['./'+os.path.basename(actual_path)] = {'hash': Common.hashfile(actual_path),
                                                                                'fullpath': actual_path }
                        if os.path.isdir(expected_path):
                            for root, subdirs, files in os.walk(expected_path):
                                for file in files:
                                    expected_files[os.path.relpath(root, expected_path)+'/'+file] = {'hash': Common.hashfile(root+'/'+file),
                                                                                                     'fullpath': root+'/'+file }
                        else:
                            expected_files['./'+os.path.basename(expected_path)] = {'hash': Common.hashfile(expected_path),
                                                                                    'fullpath': expected_path }
                        
                        for file in actual_files:
                            if not file in expected_files:
                                Common.message(padding+"   FAILED: file should not be present in output: "+file)
                                success = False
                            elif expected_files[file]['hash'] != actual_files[file]['hash']:
                                Common.message(padding+"   FAILED: content in actual and expected files differ: "+file)
                                success = False
                                mime = mimetypes.guess_type(file)
                                if mime[0].startswith('text/') and os.stat(actual_files[file]['fullpath']).st_size < 1000000 and os.stat(expected_files[file]['fullpath']).st_size < 1000000:
                                    with open(expected_files[file]['fullpath'], 'r') as expected_file:
                                        with open(actual_files[file]['fullpath'], 'r') as actual_file:
                                            expected_lines = expected_file.readlines()
                                            actual_lines = actual_file.readlines()
                                            max_lines = 30
                                            for diffline in difflib.unified_diff(expected_lines, actual_lines, fromfile=file, tofile=file):
                                                Common.message(padding+diffline.strip())
                                                max_lines -= 1
                                                if max_lines <= 0:
                                                    break
                        for file in expected_files:
                            if not file in actual_files:
                                Common.message(padding+"   FAILED: file should be present in output: "+file)
                                success = False
                        if not success:
                            actual_compact = list(actual_files.keys())
                            actual_compact.sort()
                            actual_compact = ', '.join(actual_compact)
                            if len(actual_compact) > 80:
                                actual_compact = actual_compact[:79]+'…'
                            expected_compact = list(expected_files.keys())
                            expected_compact.sort()
                            expected_compact = ', '.join(expected_compact)
                            if len(expected_compact) > 80:
                                expected_compact = expected_compact[:79]+'…'
                            Common.message(padding+"   ACTUAL:   "+actual_compact)
                            Common.message(padding+"   EXPECTED: "+expected_compact)
                    
                    if 'status' in step:
                        if not current_status_path:
                            Common.message(padding+"   ERROR: no status directory available")
                        actual_status = None
                        for root, subdirs, files in os.walk(current_status_path):
                            for file in files:
                                with open(root+'/'+file, 'r') as f:
                                    actual_status = f.readline().strip()
                                    break
                            if actual_status:
                                break
                        if actual_status != step['status']:
                            Common.message(padding+"   FAILED: actual status and expected status differ: \n  expected: "+step['status']+"\n    actual: "+actual_status)
                            success = False
                    
                    if not success:
                        tests_failed += 1
                    tests_run += 1
                    
        return {
            'tests': {
                'skipped': tests_skipped,
                'run': tests_run,
                'failed': tests_failed
            }
        }
    
    def run_tests(self):
        focus = None
        for test_name in self.tests:
            for test_id in self.tests[test_name]:
                if 'focus' in self.tests[test_name][test_id]:
                    focus = test_name
                    Common.message(_('Focusing on test:')+' '+test_name)
                    break
        
        tests_run = 0
        tests_failed = 0
        tests_skipped = 0
        
        for test_name in self.tests:
            if test_name == '*':
                continue
            if focus and test_name != focus:
                continue
            Common.message("\n---\n"+_('Running test:')+' '+test_name+"\n")
            
            test = self.tests[test_name]
            
            temp_path = tempfile.mkdtemp(prefix='test-')
            tests_path = os.path.dirname(self.path)+"/tests"
            
            config_path = None # tests_path+"/"+test_name+"/config"
            input_path = tests_path+"/"+test_name
            output_path = temp_path+"/"+test_name+"/output"
            status_path = temp_path+"/"+test_name+"/status"
            os.makedirs(output_path)
            os.makedirs(status_path)
            
            result = self.run(config_path, input_path, output_path, status_path, test=test_name)
            tests_run += result['tests']['run']
            tests_failed += result['tests']['failed']
            tests_skipped += result['tests']['skipped']
            
            Common.message("")
            Common.message(_('Host system path to pipeline output is:')+' '+Common.host_path(os.path.dirname(output_path)))
        
        Common.message("")
        if focus:
            Common.message(_('Test in focus:')+' '+test_name)
        Common.message("TESTS RUN: "+str(tests_run))
        Common.message("TESTS FAILED: "+str(tests_failed))
        #Common.message("TESTS SKIPPED: "+str(tests_skipped))

    def dump(self):
        #pprint(self.config)
        #pprint(self.steps)
        #pprint(self.tests)
        pass
