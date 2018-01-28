import tornado.web
import tornado.websocket
import tornado.httpserver
import tornado.ioloop
import json as json_lib
import dronekit
import sys
import SetInterval as setInterval

clients = []

# Key/secret pairs with comments for labeling
keys = {
"sIegcsimlHCAc9PBXWRB":"2Aooe5DiLV5DXUPp9mMs"
}

# Example Validate Message: {"type":"validate", "key":"sIegcsimlHCAc9PBXWRB", "secret":"2Aooe5DiLV5DXUPp9mMs"}

soloTMP = dronekit.connect("udpout:10.1.1.10:14560")

class WebSocketHandler(tornado.websocket.WebSocketHandler):
    def open(self):
        clients.append(self)
        self.id = len(clients)
        # define API key stuff
        self.api = APIBackend(soloTMP, self) # temporarily pass only one connection to the API
        print("New client(#" + str(self.id) + ") joined from " + str(self.request.remote_ip))

    def on_message(self, message):
        print("RX: " + str(message))

        # Decode the JSON into a dictionary, and raise an exception and disconnect the client if it fails
        try:
            json = json_lib.loads(message)
        except ValueError:
            print("Error: Client " + str(self.id) + " sent invalid JSON! Terminating connection...")
            self.close(1003, "Invalid JSON object!")
        except:
            print("Unknown JSON parsing error from Client #" + str(self.id) + "!")
            raise
        else:
            self.api.processJSON(json)


    def on_close(self):
        print("Closing WebSocket...")
        try:
            print("Canceling any listener(s) leftover...")
            self.listener.cancel()
        except AttributeError:
            print("No listener to cancel! Socket closing.")


class IndexPageHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("index.html")


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r'/', IndexPageHandler),
            (r'/websocket', WebSocketHandler)
        ]

        settings = {
            'template_path': 'templates'
        }
        tornado.web.Application.__init__(self, handlers, **settings)

def broadcast(message):
    for client in clients:
        client.write_message(str(message))

class APIBackend:
    def __init__(self, dronekit_obj, socket):
        self.vehicle = dronekit_obj
        self.socket = socket
    key = None
    secret = None
    validated = False
    listener = None
    def processJSON(self, json):
        if (not self.validated):
            if (json["type"] == "validate"):
                # If a key/secret pair was even included in the message...
                if ("key" in json and "secret" in json):
                    # If we have a matching key/secret pair
                    if (json["key"] in keys) and (keys[json["key"]] == json["secret"]):
                        self.validated = True
                        self.socket.write_message('{"type":"validate", "status":true}')
                        print("Client #" + str(self.socket.id) + " validated!")
                else:
                    self.validated = False
                    self.socket.write_message('{"type":"validate", "status":false}')
                    print("Client #" + str(self.socket.id) + " attempted validation, but failed due to invalid or mismatched key/secret pair!")
            else:
                # Inform the client they are not validated
                self.socket.write_message('{"type":"validate", "status":false}')
        else:
            # The actual API begins here
            if (json["type"] == "get"):
                    # Eventually this will be an IF chain for returning individual things
                    if "listener" in json:
                        print("Listener key present!")
                        if (json["listener"] == None):
                            print("Canceling listener...")
                            try:
                                self.listener.cancel()
                                self.listener = None
                            except AttributeError:
                                print("No listener to cancel! Ignoring...")
                        # As long as it's a number as expected, and we don't already have a listener running
                        elif (type(json["listener"]) is float or type(json["listener"]) is int):
                            self.listener = setInterval.setInterval(self.returnAttributes, float(json["listener"]))
                            print("Starting listener...")
                    else:
                        reply_dict = self.fetchAttributes()
                        reply_json = json_lib.dumps(reply_dict)
                        self.socket.write_message(reply_json)
                        # If the client just sends a get request with a blank list of attributes, assume they want ALL attributes
            elif (json["type"] == "close"):
                self.socket.close()

    def fetchAttributes(self):
        """Fetch attributes from Vehicle drone and return as a type:return reply with fromListener:false"""
        attributes_dict = {
            "version":{
                "version":str(self.vehicle.version),
                "major":str(self.vehicle.version.major),
                "minor":str(self.vehicle.version.minor),
                "patch":str(self.vehicle.version.patch),
                "release_type":str(self.vehicle.version.release_type()),
                "release_version":str(self.vehicle.version.release_version()),
                "is_stable":str(self.vehicle.version.is_stable())
            },
            "capabilities":{
                "mission_float":self.vehicle.capabilities.mission_float,
                "param_float":self.vehicle.capabilities.param_float,
                "mission_int":self.vehicle.capabilities.mission_int,
                "command_int":self.vehicle.capabilities.command_int,
                "param_union":self.vehicle.capabilities.param_union,
                "ftp":self.vehicle.capabilities.ftp,
                "set_attitude_target":self.vehicle.capabilities.set_attitude_target,
                "set_attitude_target_local_ned":self.vehicle.capabilities.set_attitude_target_local_ned,
                "set_altitude_target_global_int":self.vehicle.capabilities.set_altitude_target_global_int,
                "terrain":self.vehicle.capabilities.terrain,
                "set_actuator_target":self.vehicle.capabilities.set_actuator_target,
                "flight_termination":self.vehicle.capabilities.flight_termination,
                "mission_float":self.vehicle.capabilities.mission_float,
                "compass_calibration":self.vehicle.capabilities.compass_calibration,
            },
            "location":{
                # Absolute global location
                "global_frame":{
                    "lat":self.vehicle.location.global_frame.lat,
                    "lon":self.vehicle.location.global_frame.lon,
                    "alt":self.vehicle.location.global_frame.alt,
                },
                # Absolute lat and lon, relative altitude
                "global_relative_frame":{
                    "lat":self.vehicle.location.global_relative_frame.lat,
                    "lon":self.vehicle.location.global_relative_frame.lon,
                    "alt":self.vehicle.location.global_relative_frame.alt,
                },
                # Relative location to home
                "local_frame":{
                    "north":self.vehicle.location.local_frame.north,
                    "east":self.vehicle.location.local_frame.east,
                    "down":self.vehicle.location.local_frame.down,
                },
            },
            "attitude":{
                "pitch":self.vehicle.attitude.pitch,
                "yaw":self.vehicle.attitude.yaw,
                "roll":self.vehicle.attitude.roll,
            },
            "velocity":self.vehicle.velocity,
            "gps_0":{
                "eph":self.vehicle.gps_0.eph,
                "epv":self.vehicle.gps_0.epv,
                "fix_type":self.vehicle.gps_0.fix_type,
                "satellites_visible":self.vehicle.gps_0.satellites_visible,
            },
            # note: untested since I don't have a gimbal (yet), but should work fine
            "gimbal":{
                "pitch":self.vehicle.gimbal.pitch,
                "roll":self.vehicle.gimbal.roll,
                "yaw":self.vehicle.gimbal.yaw,
            },
            "battery":{
                "voltage":self.vehicle.battery.voltage,
                "current":self.vehicle.battery.current,
                "level":self.vehicle.battery.level,
            },
            "ekf_ok":self.vehicle.ekf_ok,
            "last_heartbeat":self.vehicle.last_heartbeat,
            "rangefinder":{
                "distance":self.vehicle.rangefinder.distance,
                "voltage":self.vehicle.rangefinder.voltage,
            },
            "heading":self.vehicle.heading,
            "is_armable":self.vehicle.is_armable,
            "system_status":self.vehicle.system_status.state,
            "groundspeed":self.vehicle.groundspeed,
            "airspeed":self.vehicle.airspeed,
            "mode":self.vehicle.mode.name,
            "armed":self.vehicle.armed,
        }
        print("Sending " + str(sys.getsizeof(attributes_dict)) + " byte attribute object...")
        reply_dict = {
            "type":"return",
            "fromListener":False,
            "attributes":attributes_dict
        }
        return reply_dict

    def returnAttributes(self):
        """Used by the setInterval listener function to automatically send a client updated attributes. Calls fetchAttributes() and writes the message to this APIBackend's socket."""
        reply_dict = self.fetchAttributes()
        reply_dict["fromListener"] = True
        self.socket.write_message(reply_dict)


if __name__ == '__main__':
    ws_app = Application()
    server = tornado.httpserver.HTTPServer(ws_app)
    server.listen(8080)
    tornado.ioloop.IOLoop.instance().start()
