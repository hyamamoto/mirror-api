#!/usr/bin/python

# Copyright (C) 2013 Gerwin Sturm, FoldedSoft e.U.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Notification/subscription handler

Handles subscription post requests coming from the Mirror API and forwards
the requests to the relevant demo services.

"""

__author__ = 'scarygami@gmail.com (Gerwin Sturm)'

import utils
from demos import demo_services
from auth import get_auth_service

import json
import logging
from datetime import datetime
from google.appengine.ext import ndb


class TimelineNotifyHandler(utils.BaseHandler):
    def post(self):
        """Callback for Timeline updates."""
        message = self.request.body
        data = json.loads(message)
        logging.info(data)

        self.response.status = 200

        gplus_id = data["userToken"]
        verifyToken = data["verifyToken"]
        user = ndb.Key("User", gplus_id).get()
        if user is None or user.verifyToken != verifyToken:
            logging.info("Wrong user")
            return

        if data["collection"] != "timeline":
            logging.info("Wrong collection")
            return

        service = get_auth_service(gplus_id)

        if service is None:
            logging.info("No valid credentials")
            return

        result = service.timeline().get(id=data["itemId"]).execute()
        logging.info(result)

        for demo_service in demo_services:
            if hasattr(demo_service, "handle_item"):
                (new_items, updated_items, deleted_items) = demo_service.handle_item(result)
                if new_items is not None:
                    for item in new_items:
                        new_result = service.timeline().insert(body=item).execute()
                        logging.info(new_result)
                # TODO: handle updating, deleting


class LocationNotifyHandler(utils.BaseHandler):
    def post(self):
        """Callback for Location updates."""
        message = self.request.body
        data = json.loads(message)

        self.response.status = 200

        gplus_id = data["userToken"]
        verifyToken = data["verifyToken"]
        user = ndb.Key("User", gplus_id).get()
        if user is None or user.verifyToken != verifyToken:
            logging.info("Wrong user")
            return

        if data["collection"] != "locations":
            logging.info("Wrong collection")
            return

        if data["operation"] != "UPDATE":
            logging.info("Wrong operation")
            return

        service = get_auth_service(gplus_id)

        if service is None:
            logging.info("No valid credentials")
            return

        result = service.locations().get(id=data["itemId"]).execute()
        logging.info(result)

        if "longitude" in result and "latitude" in result:
            user.longitude = result["longitude"]
            user.latitude = result["latitude"]
            user.locationUpdate = datetime.utcnow()
            user.put()

        for demo_service in demo_services:
            if hasattr(demo_service, "handle_location"):
                (new_items, updated_items, deleted_items) = demo_service.handle_location(result)
                if new_items is not None:
                    for item in new_items:
                        new_result = service.timeline().insert(body=item).execute()
                        logging.info(new_result)

                # TODO: handle updating, deleting


NOTIFY_ROUTES = [
    ("/timeline_update", TimelineNotifyHandler),
    ("/locations_update", LocationNotifyHandler)
]
