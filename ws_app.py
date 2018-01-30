import tornado.web
import tornado.websocket
import tornado.httpserver
import tornado.ioloop
import json as json_lib
import dronekit
import sys
import SetInterval as setInterval

all_clients = []
validated_clients = []

# Key/secret pairs with comments for labeling
keys = {
"sIegcsimlHCAc9PBXWRB":"2Aooe5DiLV5DXUPp9mMs"
}

# Example Validate Message: {"type":"validate", "key":"sIegcsimlHCAc9PBXWRB", "secret":"2Aooe5DiLV5DXUPp9mMs"}

def broadcast(message, clientsArg):
    """Send a broadcast to all websockets clients in the list clientsArg"""
    for client in clientsArg:
        client.write_message(str(message))

class DroneKitWrapper:
    """Wrapper to more easily manage persistent connections to a DroneKit vehicle, and broadcast to other parts of the application when we lose connection"""
    def __init__(self, connectionString):
        self.connectionString = connectionString
        try:
            self.vehicle = dronekit.connect(self.connectionString, wait_ready=True, status_printer=self.status_printer, heartbeat_timeout=3)
        except:
            print("DroneKitWrapper: Error connecting to vehicle!")
            self.connected = False
            self.updateConnectionStatus()
        else:
            print("DroneKitWrapper: Successfully connected to vehicle.")
            self.connected = True
            self.updateConnectionStatus()

    connectionString = None
    connected = False
    vehicle = None
    def status_printer(self, txt):
        """Function used as the status_printer argument for dronekit's connect(). Simply appends a prefix to messages from DroneKit to make log filtering easier."""
        print("DroneKitWrapper: " + txt)

    def check(self):
        """Main safety component of this class. Checks the status of the connection every one second and updates other parts of the application."""
        #Temporary marker for me
        print("DKW: check")

        if (self.vehicle is not None): #If the vehicle even connected initially
            print("DroneKitWrapper: Last Heartbeat: " + str(self.vehicle.last_heartbeat))
            # We have been connected to the vehicle at SOME point...
            if (self.vehicle.last_heartbeat > 2):
                # Heartbeats should happen at 4Hz, so after 2 seconds it's a safe bet something's wrong. Dronekit times out at 3 seconds so >3 never happens.
                self.connected = False
            else:
                # If all these bad conditions haven't happened, we must be connected alright
                self.connected = True
        else:
            # We haven't even made the initial connection to the vehicle
            self.connected = False

        # Send what we found to clients with broadcast
        self.updateConnectionStatus()

        # Now we start trying to reconnect if we need to
        if (self.connected == False):
            print("DroneKitWrapper: Attempting reconnection to vehicle...")
            try:
                self.vehicle = dronekit.connect(self.connectionString, wait_ready=True, status_printer=self.status_printer, heartbeat_timeout=3)
            except:
                print("DroneKitWrapper: Error connecting to vehicle!")
                self.connected = False
                self.updateConnectionStatus()
            else:
                print("DroneKitWrapper: Successfully connected to vehicle.")
                self.connected = True
                self.updateConnectionStatus()

    def updateConnectionStatus(self):
        """Send a broadast to all clients with update of connection status"""
        msg_dict = {
            "type":"connection",
            "data":{
            "connected":self.connected
            }
        }
        msg_json = json_lib.dumps(msg_dict)
        broadcast(msg_json, validated_clients)
        print("DroneKitWrapper: Connected = " + str(self.connected))

print("Attempting connection to drone...")
drone = DroneKitWrapper("udpout:10.1.1.10:14560")

class WebSocketHandler(tornado.websocket.WebSocketHandler):
    def open(self):
        all_clients.append(self)
        self.id = len(all_clients)
        # define API key stuff
        self.api = APIBackend(drone, self) # temporarily pass only one connection to the API
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
            self.api.listener.cancel()
        except AttributeError:
            print("No listener to cancel! Socket closing.")
        # Remove self from list of clients
        all_clients.remove(self)
        try:
            validated_clients.remove(self)
        except:
            pass


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

class APIBackend:
    def __init__(self, dronekitWrapper, socket):
        self.vehicleWrapper = dronekitWrapper
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
                        # Add them to the list of validated clients
                        validated_clients.append(self.socket)
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
            # First we make sure we're actually connected to our vehicle by checking the vehicleWrapper class
            if (self.vehicleWrapper.connected):
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
            else:
                # Only certain API functions work here, like setting listeners
                if "listener" in json:
                    print("Listener key present! Starting listener despite no connection to drone...")
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
                        print("Starting listener (WARNING: No connection, so listener will do nothing until drone reconnects)...")
                drone.updateConnectionStatus()


    def fetchAttributes(self):
        """Fetch attributes from Vehicle drone and return as a type:return reply with fromListener:false"""
        attributes_dict = {
            "version":{
                "version":str(self.vehicleWrapper.vehicle.version),
                "major":str(self.vehicleWrapper.vehicle.version.major),
                "minor":str(self.vehicleWrapper.vehicle.version.minor),
                "patch":str(self.vehicleWrapper.vehicle.version.patch),
                "release_type":str(self.vehicleWrapper.vehicle.version.release_type()),
                "release_version":str(self.vehicleWrapper.vehicle.version.release_version()),
                "is_stable":str(self.vehicleWrapper.vehicle.version.is_stable())
            },
            "capabilities":{
                "mission_float":self.vehicleWrapper.vehicle.capabilities.mission_float,
                "param_float":self.vehicleWrapper.vehicle.capabilities.param_float,
                "mission_int":self.vehicleWrapper.vehicle.capabilities.mission_int,
                "command_int":self.vehicleWrapper.vehicle.capabilities.command_int,
                "param_union":self.vehicleWrapper.vehicle.capabilities.param_union,
                "ftp":self.vehicleWrapper.vehicle.capabilities.ftp,
                "set_attitude_target":self.vehicleWrapper.vehicle.capabilities.set_attitude_target,
                "set_attitude_target_local_ned":self.vehicleWrapper.vehicle.capabilities.set_attitude_target_local_ned,
                "set_altitude_target_global_int":self.vehicleWrapper.vehicle.capabilities.set_altitude_target_global_int,
                "terrain":self.vehicleWrapper.vehicle.capabilities.terrain,
                "set_actuator_target":self.vehicleWrapper.vehicle.capabilities.set_actuator_target,
                "flight_termination":self.vehicleWrapper.vehicle.capabilities.flight_termination,
                "mission_float":self.vehicleWrapper.vehicle.capabilities.mission_float,
                "compass_calibration":self.vehicleWrapper.vehicle.capabilities.compass_calibration,
            },
            "location":{
                # Absolute global location
                "global_frame":{
                    "lat":self.vehicleWrapper.vehicle.location.global_frame.lat,
                    "lon":self.vehicleWrapper.vehicle.location.global_frame.lon,
                    "alt":self.vehicleWrapper.vehicle.location.global_frame.alt,
                },
                # Absolute lat and lon, relative altitude
                "global_relative_frame":{
                    "lat":self.vehicleWrapper.vehicle.location.global_relative_frame.lat,
                    "lon":self.vehicleWrapper.vehicle.location.global_relative_frame.lon,
                    "alt":self.vehicleWrapper.vehicle.location.global_relative_frame.alt,
                },
                # Relative location to home
                "local_frame":{
                    "north":self.vehicleWrapper.vehicle.location.local_frame.north,
                    "east":self.vehicleWrapper.vehicle.location.local_frame.east,
                    "down":self.vehicleWrapper.vehicle.location.local_frame.down,
                },
                "home":{
                    "lat":None,
                    "lon":None,
                    "alt":None,
                }
            },
            "attitude":{
                "pitch":self.vehicleWrapper.vehicle.attitude.pitch,
                "yaw":self.vehicleWrapper.vehicle.attitude.yaw,
                "roll":self.vehicleWrapper.vehicle.attitude.roll,
            },
            "velocity":self.vehicleWrapper.vehicle.velocity,
            "gps_0":{
                "eph":self.vehicleWrapper.vehicle.gps_0.eph,
                "epv":self.vehicleWrapper.vehicle.gps_0.epv,
                "fix_type":self.vehicleWrapper.vehicle.gps_0.fix_type,
                "satellites_visible":self.vehicleWrapper.vehicle.gps_0.satellites_visible,
            },
            # note: untested since I don't have a gimbal (yet), but should work fine
            "gimbal":{
                "pitch":self.vehicleWrapper.vehicle.gimbal.pitch,
                "roll":self.vehicleWrapper.vehicle.gimbal.roll,
                "yaw":self.vehicleWrapper.vehicle.gimbal.yaw,
            },
            "battery":{
                "voltage":self.vehicleWrapper.vehicle.battery.voltage,
                "current":self.vehicleWrapper.vehicle.battery.current,
                "level":self.vehicleWrapper.vehicle.battery.level,
            },
            "ekf_ok":self.vehicleWrapper.vehicle.ekf_ok,
            "last_heartbeat":self.vehicleWrapper.vehicle.last_heartbeat,
            "rangefinder":{
                "distance":self.vehicleWrapper.vehicle.rangefinder.distance,
                "voltage":self.vehicleWrapper.vehicle.rangefinder.voltage,
            },
            "heading":self.vehicleWrapper.vehicle.heading,
            "is_armable":self.vehicleWrapper.vehicle.is_armable,
            "system_status":self.vehicleWrapper.vehicle.system_status.state,
            "groundspeed":self.vehicleWrapper.vehicle.groundspeed,
            "airspeed":self.vehicleWrapper.vehicle.airspeed,
            "mode":self.vehicleWrapper.vehicle.mode.name,
            "armed":self.vehicleWrapper.vehicle.armed,
        }
        # More tricky variables that may or may not exist
        if (self.vehicleWrapper.vehicle.home_location):
            print("Setting home location for attribute object...")
            attributes_dict["location"]["home"]["lat"] = self.vehicleWrapper.vehicle.home_location.lat
            attributes_dict["location"]["home"]["lon"] = self.vehicleWrapper.vehicle.home_location.lon
            attributes_dict["location"]["home"]["alt"] = self.vehicleWrapper.vehicle.home_location.alt
        else:
            print("Autopilot has not set home location yet!")

        print("Sending " + str(sys.getsizeof(attributes_dict)) + " byte attribute object...")
        reply_dict = {
            "type":"return",
            "fromListener":False,
            "attributes":attributes_dict
        }
        return reply_dict

    def returnAttributes(self):
        """Used by the setInterval listener function to automatically send a client updated attributes. Calls fetchAttributes() and writes the message to this APIBackend's socket."""
        if(drone.connected):
            reply_dict = self.fetchAttributes()
            reply_dict["fromListener"] = True
            try:
                self.socket.write_message(reply_dict)
            except:
                print("Unknown error in call of returnAttributes function!")
                #self.socket.close()
                #self.listener.cancel()
        else:
            print("Not returning attributes...not connected to drone!")

if __name__ == '__main__':
    print("Starting server stuff...")
    ws_app = Application()
    server = tornado.httpserver.HTTPServer(ws_app)
    server.listen(8080)
    tornado.ioloop.PeriodicCallback(drone.check, 1000).start()
    tornado.ioloop.IOLoop.instance().start()
