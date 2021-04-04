import json, requests, sys, slack, time, os, logging.handlers, api
import tmdbsimple as tmdb
import tvdbsimple as tvdb
from datetime import datetime, timezone
from slackclient import SlackClient

logger = logging.getLogger('root')

def slack_queue():
	try:
		logger.info("Creating Slack Bot")
		while True:
			try:
				slack.Bot()
				time.sleep(1)
			except Exception as e:
				logger.error("ERROR Slack Bot: %s" % e)
				logger.error('Error on line {}'.format(sys.exc_info()[-1].tb_lineno, type(e).__name__, e))
				pass	
	except Exception as e:
		logger.error("Error Slack Queue - %s" % e)
		logger.error('Error on line {}'.format(sys.exc_info()[-1].tb_lineno, type(e).__name__, e))
		pass

def get_info(response):
	final_list = []
	for x in response:
		try:
			if 'title' in x:
				if "childRequests" in x:
					title = x["title"]
					for y in x.get("childRequests"):
						username = y["requestedUser"]["userName"]
						date_requested = y["requestedDate"]
						to_approve = y["canApprove"]
						ombi_id = y["id"]
					id = x['tvDbId']
					kind = "tv"
				else:
					username = x["requestedUser"]["userName"]
					date_requested = x["requestedDate"]
					to_approve = x["canApprove"]
					id = x["theMovieDbId"]
					title = x["title"]
					kind = "movie"

				poster = x['posterPath']
				text = x['overview']
				ombi_id = x['id']
				status = x["status"]
				release_date = x["releaseDate"]

				date_requested = datetime.strptime(date_requested[:-1],'%Y-%m-%dT%H:%M:%S.%f').replace(tzinfo=timezone.utc).astimezone(tz=None).strftime("%Y-%m-%d %I:%M:%S %p")
				release_date = datetime.strptime(release_date,'%Y-%m-%dT%H:%M:%S').strftime("%Y-%m-%d")
				title = "%s (%s)" % (x["title"], release_date)

				final_list.append((kind, id, title, text, poster, status, username, date_requested, to_approve, ombi_id))

			elif 'error' in x:
				logger.error(response)
		except Exception as e:
			logger.error("Error Getting Info - %s" % e)

	return final_list

def get_requested():
	try:
		ombi_API = API(os.environ['ombi_host'], os.environ['ombi_api'], os.environ['ombi_user'])
		final_list = []
		tv_request = ombi_API.get_tv_request()
		movie_request = ombi_API.get_movie_request()

		count = 0
		while tv_request == "" or count < 5:
			count+=1
			tv_request = ombi_API.get_tv_request()	

		count = 0
		while movie_request == "" or count < 5:
			count+=1
			movie_request = ombi_API.get_movie_request()

		final_list = final_list + get_info(tv_request)
		final_list = final_list + get_info(movie_request)

		return final_list
	except Exception as e:
		logger.error("Error Getting Requested - %s" % e)

def create_attachment(kind, id, title, text, poster, action_name, ombi_id=id, **kwargs):
	fields = []
	for key in kwargs:
		if key is not None: fields.append({'title':key.replace("_"," ") ,'value':kwargs[key],'short':'false'})

	if kind == "tv":
		title_link = 'http://thetvdb.com/index.php?tab=series&id=%s' % id
		image_url = 'http://thetvdb.com/banners/posters/%s-1.jpg' % id
		thumb_url = 'http://thetvdb.com/banners/%s' % poster
		footer = 'TVDB ID: %s' % id
		footer_icon = 'https://i.imgur.com/vJFzNCm.png'
	elif kind == "movie":
		title_link = 'https://themoviedb.org/movie/%s' % id
		image_url = 'https://image.tmdb.org/t/p/original%s' % poster
		thumb_url = 'https://image.tmdb.org/t/p/original%s' % poster
		footer = 'TMDB ID: %s' % id
		footer_icon = 'https://pbs.twimg.com/profile_images/789117657714831361/zGfknUu8.jpg'

	if action_name == "request":
		if kind == "movie":
			action_value = "m%s" % id
		elif kind == "tv":
			action_value = "t%s" % id
		actions = [{'name': 'ombi_request', 'text': 'Request!', 'value': action_value, 'style': 'primary', 'type' : 'button'}]
	elif action_name == "approve":
		if kind == "tv": image_url = poster
		actions =  [{'name': 'ombi_approve', 'text': 'Approve!', 'value': "%s;%s;%s" % (title, ombi_id, kind), 'style': 'primary', 'type' : 'button'}]
	
	data=[
	    {
	      'title': title,
	      'title_link': title_link,
	      'text': text,
	      'image_url': image_url,
	      'thumb_url': thumb_url,
	      'color': '#F88017',
          'fields': fields, 
	      'footer': footer,
	      'footer_icon': footer_icon,
	      'callback_id': id,
	      'actions': actions
	    }]
	return data

def get_single_info(test_title, test_kind):
	try:
		data = ""
		final_list = get_requested()
		for kind, id, title, text, poster, status, username, date_requested, to_approve, ombi_id in final_list:
			if test_title in title and test_kind.lower() == kind:
				if to_approve == True:
					data = create_attachment(kind, id, title, text, poster, "approve", Status=status, User=username, Date_Requested=date_requested, ombi_id=ombi_id)
					break
		return data
	except Exception as e:
		logger.error("Error Getting Unapproved - %s" % e)

def get_unapproved():
	try:
		count=0
		final_list = get_requested()
		for kind, id, title, text, poster, status,username, date_requested, to_approve, ombi_id in final_list:
			if to_approve == True:
				count+=1
				data = create_attachment(kind, id, title, text, poster, "approve", Status=status, User=username, Date_Requested=date_requested, ombi_id=ombi_id)
				sendMessage("", data)
		return count
	except Exception as e:
		logger.error("Error Getting Unapproved - %s" % e)

def approve_process(ombi_id, kind):
	ombi_API = API(os.environ['ombi_host'], os.environ['ombi_api'], os.environ['ombi_user'])
	if kind == "tv":
		seasons = ombi_API.get_tv_child(ombi_id)[0]
		#THIS APPROVES ALL, CAN YOU LIMIT  THE APPROVAL TO SPECIFIC SEASONS
		for x in seasons['seasonRequests']:
			child_request_id = x['childRequestId']
			response = ombi_API.approve_tv(child_request_id)
	elif kind == "movie":
		response = ombi_API.approve_movie(ombi_id)

	return response

def request_media(request_info):
	try:
		ombi_API = API(os.environ['ombi_host'], os.environ['ombi_api'], os.environ['ombi_user'])
		response = False
		message = None
	
		kind = request_info[:1]
		id = request_info[1:]

		if kind.upper() == "T":
			kind = "tv"
			response = ombi_API.request_tv(id)
		elif kind.upper() == "M":
			kind = "movie"
			response = ombi_API.request_movie(id)

		try:
			if response['isError']:
				message = response['errorMessage']
			else:
				message = "This has been added to Ombi."
		except:
			message = "Error Adding to Ombi"

		return (message, kind, id)
	except:
		logger.error("Error Requesting %s" % request_info)

def search_movie(string):
	tmdb.API_KEY = os.environ['tmdb_api']
	search = tmdb.Search()
	search.movie(query=string)
	if len(search.results) > 0:
		for s in search.results[:5]:
			data = create_attachment("movie", s['id'], '%s (%s)' % (s['title'], s['release_date']), s['overview'], s['poster_path'], "request")
			logger.info("Ombi Request for %s returned %s." % (string, data))
			sendMessage("", data)
	else:
		logger.info("No Results Found")
		sendMessage("No results found")
def search_tv(string):
	tvdb.KEYS.API_KEY = os.environ['tvdb_api']
	search = tvdb.Search()
	search.series(string)
	try:
		for s in search.series[:5]:
			data = create_attachment("tv", s['id'], s['seriesName'], checkElement(s, 'overview'), checkElement(s, 'banner'), "request", Status=s['status'])
			logger.info("Ombi Request for %s returned %s." % (string, data))
			sendMessage("", data)
	except:
		logger.info("No Results Found")
		sendMessage("No results found")

def checkElement(list, element):
	try:
		return list[element]
	except:
		return ""

def sendMessage(response, attachments=None, update=False, ts=False):
	try:
		if response is None and isinstance(attachments, str):
			response = attachments
			attachments = None
			
		logger.info("Sending Message (%s) and Attachments (%s) to User (%s)" % (response, attachments, os.environ['slack_bot']))

		sc = SlackClient(os.environ['slack_api_key'])
		if update:
			result = sc.api_call("chat.update", channel=os.environ['slack_channel'], text=response, as_user=False, ts=ts, attachments=json.dumps(attachments))
		else:
			result = sc.api_call("chat.postMessage", channel=os.environ['slack_channel'], text=response, as_user=False, attachments=json.dumps(attachments))
			
		if str(result['ok']) == 'True':
			return "success"
		else:
			logger.error("Failed Sending Message - %s" % result)
			return "fail"
	except Exception as e:
		logger.error("Error Sending Message - Exception: %s" % e)
		return "error"

class API(object):

	def __init__(self, host_url, api_key, user):
		"""Constructor requires Host-URL and API-KEY"""
		self.host_url = host_url
		self.api_key = api_key
		self.user = user
		
	def get_tv_request(self):
		res = self.request_get("{}/Request/tv".format(self.host_url))
		return res.json()
		
	def get_movie_request(self):
		res = self.request_get("{}/Request/movie".format(self.host_url))
		return res.json()

	def approve_movie(self, ombi_id):
		data = json.loads('{"id":%s}' % ombi_id)
		res = self.request_post("{}/Request/movie/approve".format(self.host_url), data=data)
		return res.json()

	def approve_tv(self, ombi_id):
		data = json.loads('{"id":%s}' % ombi_id)
		res = self.request_post("{}/Request/tv/approve".format(self.host_url), data=data)
		return res.json()

	def request_movie(self, theMovieDbId):
		data = json.loads('{"theMovieDbId":%s}' % theMovieDbId)
		res = self.request_post("{}/Request/movie".format(self.host_url), data=data)
		return res.json()

	def request_tv(self, tvDbId):
		data = json.loads('{"requestAll":"true","latestSeason":"true","firstSeason":"true", "tvDbId":%s, "seasons":[]}' % tvDbId)
		res = self.request_post("{}/Request/tv".format(self.host_url), data=data)
		return res.json()

	def get_tv_child(self, ombi_id):
		res = self.request_get(str("{}/Request/tv/%s/child" % ombi_id).format(self.host_url))
		return res.json()

	# REQUESTS STUFF
	def request_get(self, url, data={}):
		"""Wrapper on the requests.get"""
		headers = {
			'Accept':'application/json',
			'ApiKey': self.api_key,
			'UserName': self.user
		}
		res = requests.get(url, headers=headers, json=data)
		return res

	def request_post(self, url, data):
		"""Wrapper on the requests.post"""
		headers = {
			'Content-Type':'application/json',
			'ApiKey': self.api_key,
			'UserName': self.user
		}
		res = requests.post(url, headers=headers, json=data)
		return res

	def request_put(self, url, data):
		"""Wrapper on the requests.put"""
		headers = {
			'Accept':'application/json',
			'ApiKey': self.api_key,
			'UserName': self.user
		}
		res = requests.put(url, headers=headers, json=data)
		return res

	def request_del(self, url, data):
		"""Wrapper on the requests.delete"""
		headers = {
			'Accept':'application/json',
			'ApiKey': self.api_key,
			'UserName': self.user
		}
		res = requests.delete(url, headers=headers, json=data)
		return res
