# Copyright 2016 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import webapp2
from google.appengine.ext import ndb
import json
import time
import random
import logging
import datetime

epoch = datetime.datetime.utcfromtimestamp(0)

def unix_time_millis(dt):
    return (dt - epoch).total_seconds() * 1000.0

class Reading(ndb.Model):
	switch = ndb.StringProperty()
	draw = ndb.IntegerProperty()
	timestamp = ndb.DateTimeProperty()

class MainPage(webapp2.RequestHandler):
    def get(self):

		washer = Reading.query(Reading.switch=='Washer').order(-Reading.timestamp).get()
		dryer = Reading.query(Reading.switch=='Dryer').order(-Reading.timestamp).get()

		response = {
			'washer': {
				'draw': washer.draw,
				'timestamp': unix_time_millis(washer.timestamp)
			},
			'dryer': {
				'draw': dryer.draw,
				'timestamp': unix_time_millis(dryer.timestamp)
			}
		}

		self.response.headers['Content-Type'] = 'application/json'
		self.response.headers['Access-Control-Allow-Origin'] = '*'
		self.response.headers['Access-Control-Allow-Headers'] = '*'
		self.response.headers['Access-Control-Allow-Methods'] = 'GET'
		self.response.write(json.dumps(response))


app = webapp2.WSGIApplication([
    ('/', MainPage),
], debug=True)
