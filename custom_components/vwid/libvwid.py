# A Python class to communicate with the "We Connect ID" API.
# As there is no official API documentation, this is to a large extent inspired by
# the following PHP implementation:
# https://github.com/robske110/IDDataLogger/blob/master/src/vwid/api/MobileAppAPI.php
# Jon Petter Skagmo, 2021

import secrets
import lxml.html
import logging
import aiohttp
import asyncio

# Constants
LOGIN_BASE = "https://login.apps.emea.vwapps.io"
LOGIN_HANDLER_BASE = "https://identity.vwgroup.io"
API_BASE = "https://mobileapi.apps.emea.vwapps.io"

class vwid:
	def __init__(self, session):
		self.session = session
		self.headers = {}
		self.log = logging.getLogger(__name__)

	def form_from_response(self, text):
		page = lxml.html.fromstring(text)
		elements = page.xpath('//form//input[@type="hidden"]')
		form = {x.attrib['name']: x.attrib['value'] for x in elements}
		return (form, page.forms[0].action)

	def set_vin(self, vin):
		self.vin = vin

	def set_credentials(self, username, password):
		self.username = username
		self.password = password
		
	async def connect(self, username, password):
		self.set_credentials(username, password)
		return (await self.reconnect())

	async def reconnect(self):
		# Get authorize page
		payload = {
			'nonce': secrets.token_urlsafe(12), 
			'redirect_uri': 'weconnect://authenticated'
		}

		response = await self.session.get(LOGIN_BASE + '/authorize', params=payload)
		if response.status >= 400:
			# Non 2xx response, failed
			return False

		# Fill form with email (username)
		(form, action) = self.form_from_response(await response.read())
		form['email'] = self.username
		response = await self.session.post(LOGIN_HANDLER_BASE+action, data=form)
		if response.status >= 400:
			self.log.debug("Email fail")
			return False
			
		# Fill form with password

		(form, action) = self.form_from_response(await response.read())
		form['password'] = self.password
		response = await self.session.post(LOGIN_HANDLER_BASE+action, data=form, allow_redirects=False)
		# Handle every single redirect and stop if the redirect
		# URL uses the weconnect adapter.
		while (True):
			url = response.headers['Location']
			if (url.split(':')[0] == "weconnect"):
				if not ('access_token' in url):
					print ("Missing access token")
					return False
					# Parse query string
				query_string = url.split('#')[1]
				query = {x[0] : x[1] for x in [x.split("=") for x in query_string.split("&") ]}
				break

			if (response.status != 302):
				print ("Not redirected")
				return False

			response = await self.session.get(url, data=form, allow_redirects=False)

		self.headers = dict(response.headers)

		# Get final token
		payload = {
			'state': query['state'],
			'id_token': query['id_token'],
			'redirect_uri': "weconnect://authenticated",
			'region': "emea",
			'access_token': query["access_token"],
			'authorizationCode': query["code"]
		}
		response = await self.session.post(LOGIN_BASE + '/login/v1', json=payload)
		if response.status >= 400:
			print ('Login failed %u', response.status)
			# Non 2xx response, failed
			return False
		self.tokens = await response.json()

		# Update header with final token
		self.headers['Authorization'] = 'Bearer %s' % self.tokens["accessToken"]

		# Success
		return True
		
	async def refresh_tokens(self):
		if not self.headers:
			return False

		# Use the refresh token
		self.headers['Authorization'] = 'Bearer %s' % self.tokens["refreshToken"]
		
		response = await self.session.get(LOGIN_BASE + '/refresh/v1', headers=headers)

		if response.status >= 400:
			return False
		
		self.tokens = response.json()
			
		self.headers['Authorization'] = 'Bearer %s' % self.tokens["accessToken"]

		return True

	async def get_status(self):
		response = await self.session.get(API_BASE + "/vehicles/" + self.vin + "/status", headers=self.headers)

		# If first attempt fails, try to refresh tokens
		if response.status >= 400:
			self.log.debug("Refreshing tokens")
			if await self.refresh_tokens():
				response = await self.session.get(API_BASE + "/vehicles/" + self.vin + "/status", headers=self.headers)
			
		# If refreshing tokens failed, try a full reconnect
		if response.status >= 400:
			self.log.info("Reconnecting")
			if await self.reconnect():
				response = await self.session.get(API_BASE + "/vehicles/" + self.vin + "/status", headers=self.headers)
			
		if response.status >= 400:
			self.log.error("Get status failed")
			return {}
			
		return (await response.json())
