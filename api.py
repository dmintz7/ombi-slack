import logging, re, html, ombi, json, os, requests

logger = logging.getLogger('root')

def slack_bot(json_text):
	data = None
	message_type = json_text['type']
	
	if message_type == 'message' or message_type == 'interactive_message':
		original_message = json_text['original_message']
		ts = original_message['ts']
		actions = json_text['actions'][0]
		name = actions['name']
		callback_id = original_message['attachments'][0]['callback_id']

		logger.info("Slack Bot Name: %s, Callback ID: %s, Timestamp: %s" % (name, callback_id, ts))
		data = process_ombi(json_text)
		
		ombi.sendMessage("", data, True, ts)
		logger.info("Message Update Sent")

def process_ombi(json_text):
	data = json_text['original_message']['attachments']
	name = json_text['actions'][0]['name']
	value = json_text['actions'][0]['value']
	logger.info("Received Command: %s with Value: %s" % (name, value))
	if name == "ombi_request":
		(message, kind, ombi_id) = ombi.request_media(value)
	elif name == "ombi_approve":
		request_info = html.unescape(value).split(";")
		title = request_info[0]
		ombi_id = request_info[1]
		kind = request_info[2]

		logger.info("Attempting to Approve %s %s (%s)" % (kind, title, ombi_id))
		response = ombi.approve_process(ombi_id, kind)
		try:
			repeat = response['error'] #This will result in an error if approve process worked the first time
			logger.error("Error Response: %s" % repeat)
			logger.error("Rerunning Approve")
			response = ombi.approve_process(ombi_id, kind)
		except:
			pass

		if response['isError'] == False:
			message = response['message']
			if message == None: message = "This has been approved."
		elif response['isError'] == True:
			message = response['errorMessage']
		else:
			message = "This has not been approved due to an error."

	message = re.sub('".*"', 'This', message)[:30]
	data[0]['actions'][0]['text'] = message
	return data