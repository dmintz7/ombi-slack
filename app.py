import json, ombi, api, os, logging, sys
from flask import Flask, request, make_response
from multiprocessing import Process
from flask_apscheduler import APScheduler
from logging.handlers import RotatingFileHandler


class Config(object):
    JOBS = [
        {
            'id': 'job1',
            'func': ombi.get_unapproved,
            'trigger': 'cron',
            'hour': 8,
            'minute': 45 
        }
    ]

logger = logging.getLogger('root')
formatter = logging.Formatter('%(asctime)s - %(levelname)10s - %(module)15s:%(funcName)30s:%(lineno)5s - %(message)s')
logger = logging.getLogger()
logger.setLevel(logging.INFO)
consoleHandler = logging.StreamHandler(sys.stdout)
consoleHandler.setFormatter(formatter)	
logger.addHandler(consoleHandler)
logging.getLogger("requests").setLevel(logging.WARNING)
logger.setLevel("INFO")
fileHandler = RotatingFileHandler('/mnt/Server/Scripts/ombi-slack/logs/ombi.log', maxBytes=1024 * 1024 * 2, backupCount=1)
fileHandler.setFormatter(formatter)
logger.addHandler(fileHandler)

app = Flask(__name__)
app.config.from_object(Config())
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

@app.route('/ombi-slack', methods=['POST'])
def api_command():
	json_text = json.loads(request.form["payload"])
	p4 = Process(target=api.slack_bot, args=[json_text])
	p4.start()
	return make_response("", 200)

if __name__ == "__main__":
	p3 = Process(target=ombi.slack_queue)
	p3.start()

	logger.info("Starting Ombi Slack Server")
	app.run(host= '0.0.0.0', port=8750)