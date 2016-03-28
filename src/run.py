#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys
import os
import shutil
from pprint import pprint
from subprocess import call, check_call, check_output
import gettext

from pipeline import Pipeline
from common import Common
from web import Web

global _

def main(argv):
    Common.init("/mnt/config/config.yml", docker_container=argv[1])
    
    Common.message(_('Loading pipeline...'))
    pipeline = Pipeline(path="/mnt/pipeline/pipeline.yml", host_path=argv[0])
    
    if len(argv) > 2 and argv[2] == "test":
        pipeline.run_tests()
        
    elif len(argv) > 2 and argv[2]:
        Common.message(_('Unknown argument')+": "+argv[2])
        
    else:
        Web(pipeline, host='0.0.0.0')


if __name__ == "__main__":
    main(sys.argv[1:])
