import time, logging, ombi, os
from slackclient import SlackClient
from datetime import datetime

logger = logging.getLogger('root')

class Bot(object):
	def __init__ (self):
		self.slack_client = SlackClient(os.environ['slack_api_key'])
		self.bot_name = os.environ['slack_bot']
		self.bot_id = self.get_bot_id()
		
		if self.bot_id is None:
			exit("Error, could not find " + self.bot_name)
	
		self.event = Event(self)
		self.listen()
	
	def get_bot_id(self):
		api_call = self.slack_client.api_call("users.list")
		if api_call.get('ok'):
			users = api_call.get('members')
			for user in users:
				if 'name' in user and user.get('name') == self.bot_name:
					return "<@" + user.get('id') + ">"
			
			return None
			
	def listen(self):
		if self.slack_client.rtm_connect(with_team_state=False):
			logger.info("Successfully connected, listening for commands")
			while True:
				self.event.wait_for_event()
				time.sleep(1)
		else:
			exit("Error, Connection Failed")

class Command(object):
	def __init__(self):
		self.message = None
		self.date_sent = None
		self.commands = { 
			"search": self.search,
			"unapproved": self.ombi_unapproved,
			"help" : self.help
		}

	def handle_command(self, user, text, date_sent):
		response = ""
		try:
			if user == os.environ['slack_bot']:
				try:
					logger.info("Ombi Command Found")
					clean_text = text.replace("The user '","").replace("' has requested a ",";").replace(" at Request Date: ", ";").replace(": ",";").split(";")
					test_title = "(".join(clean_text[2].split("(")[:-1])[:-1]
					test_kind=clean_text[1].replace(" show","")
					response = ombi.get_single_info(test_title, test_kind)
				except Exception as e:
					logger.info("Error Handling Command - %s" % e)
					response = ""
			else:
				self.message = MESSAGE(text)
				self.date_sent = date_sent
				command = self.message.command().lower()
				if command in self.commands:
					response = self.commands[command]()
		except Exception as e:
			logger.info("Error Handling Command - %s" % e)
			response = ""
			

		return response

	def ombi_unapproved(self):
		logger.info("Ombi Unapproved Received")
		response = ""
		unapproved = ombi.get_unapproved()
		if unapproved == 0: response = "No Media to Approve"
		return response

	def search(self):
		logger.info("Search Request Received")
		response = ""
		if self.message.subcommand() == "MOVIE":
			ombi.search_movie(self.message.final(2))
		elif self.message.subcommand() == "TV":
			ombi.search_tv(self.message.final(2))
		else:
			response = "Invalid search Type"
		return response

	def help(self):	
		response = "Currently I support the following commands:\r\n"
		
		for command in self.commands:
			response += command + "\r\n"
			
		return response

class Event:
	def __init__(self, bot):
		self.bot = bot
		self.command = Command()
		self.event = ""

	def wait_for_event(self):
		events = self.bot.slack_client.rtm_read()
		if events and len(events) > 0:
			for event in events:
				try:
					self.parse_event(event)
				except:
					raise
					pass

	def parse_event(self, event):
		if event and 'text' in event:
			try:
				try:
					user = event['user']
				except:
					user = event['username']
			except:
				user = os.environ['slack_bot']
				
			try:
				text = event['text'].split(self.bot.bot_id)[1].strip()
			except:
				text = event['text']
			self.event = event
			channel = event['channel']
			date_sent = event['event_ts']
			self.handle_event(user, text, channel, date_sent)

	def handle_event(self, user, command, channel, date_sent):
		if command and channel:
			try:
				date_sent_format = datetime.fromtimestamp(float(date_sent))
				logger.info("Received command: " + command + " in channel: " + channel + " from user: " + user + " at " + date_sent_format.strftime("%Y-%m-%d %I:%M:%S %p"))
				response = self.command.handle_command(user, command, date_sent_format)
				if response != "": ombi.sendMessage(None, response)
			except:
				logger.error("Error Slack Handling Event")

class MESSAGE(object):
	def __init__(self, message):
		self.message = message
		self.messageParts = self.message.split()
		for x in range(1,6):
			if x > len(self.messageParts): self.messageParts.append(None)

	def command(self):
		return self.messageParts[0].upper()

	def subcommand(self):
		return None if self.messageParts[1] is None  else self.messageParts[1].upper()

	def final(self, num):
		return self.message.split(" ", num)[-1]
		
