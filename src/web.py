import os
from pprint import pprint
from common import Common

from flask import Flask, render_template, jsonify
app = Flask(__name__)

global web

class Web:
    
    def __init__(self, pipeline, host='0.0.0.0'):
        global web
        web = self
        self.pipeline = pipeline
        app.run(host=host, debug=True)

@app.route("/")
def index():
    return render_template('index.html', name=os.path.basename(web.pipeline.path), pipeline=web.pipeline.get_serializable(tests=False))
