var Drone = function (ws_url, latency, APIpassword, messageHandler, failedPasswordCallback) {
    latency = latency / 1000; //latency in ms instead of sec
    if (failedPasswordCallback == undefined) {
        failedPasswordCallback = function () {}
    }
    this.crypt = {
        "plainhash": sha256(APIpassword), //never even store it in plain text
        "salt": undefined,
    }
    if (messageHandler == undefined) {
        this.messageHandler = function (e) {}; //by default this does nothing
    } else {
        this.messageHandler = messageHandler;
    }
    this.callbacks = {
        failedPassword: failedPasswordCallback, //called if password doesn't validate us correctly
        socket: {
            onmessage: messageHandler,
            onclose: function (event) {}
        },
        ready: function () {}, //called when we actually have a listener set up and a steady stream of info coming from the drone
    }
    this.socket = new WebSocket(ws_url)
    var mainDroneObject = this; //so we can access root object from within functions
    this.socket.onopen = function (e) {
        //Do we do anything here?
    }

    this.socket.onmessage = function (msg) {
        if (mainDroneObject.logAllMessages) {
            console.log("RX: " + (msg.data))
        }
        var json = JSON.parse(msg.data);
        if (json.type == "validate") {
            mainDroneObject.validate.status = json.status;
            if (mainDroneObject.validate.status == true) {
                mainDroneObject.socket.send(JSON.stringify({
                    "type": "get",
                    "listener": latency
                })) //set up a listener with the latency we called
                mainDroneObject.callbacks.ready()
            }
            // This is a trick to check if our password verified correctly.
            // If validation status is false, but we have already cleared out the plain hash to null, that means we attempted authenticiation and failed.
            // So now we call the appropriate callback
            else if (mainDroneObject.validate.status == false && mainDroneObject.crypt.plainhash == null) {
                mainDroneObject.callbacks.failedPassword()
            }
        }
        else if (json.type == "hello") {
            mainDroneObject.crypt.salt = json.salt;
            var token = sha256(mainDroneObject.crypt.plainhash + mainDroneObject.crypt.salt)
            var message = {
                "type": "validate",
                "token": token,
            }
            mainDroneObject.socket.send(JSON.stringify(message))
            //Now we clear out all the crypt values
            mainDroneObject.crypt.plainhash = null;
            mainDroneObject.crypt.salt = null;
        }
        else if (json.type == "return") {
            mainDroneObject.vehicle.attributes = json.attributes
            mainDroneObject.vehicle.connected = true //if we are RXing data we must be connected
        }
        else if (json.type == "connection") {
            mainDroneObject.vehicle.connected = json.data.connected
        }
        //Now feed data to user-settable handler
        mainDroneObject.callbacks.socket.onmessage(msg)
    }
    this.socket.onclose = function (msg) {
        mainDroneObject.callbacks.socket.onclose(msg)
        mainDroneObject.vehicle.connected = false
    }
    this.validate = {
        status: false,
    }
    this.vehicle = {
        attributes: undefined,
        connected:false,
    };
    this.logAllMessages = false;
    this.set = {
        mode: function (arg) {
            mainDroneObject.socket.send(JSON.stringify({
                "type": "set",
                "attributes": {
                    "mode": arg.toUpperCase(),
                }
            }))
        },
        armed: function (arg) {
            if (arg == true || arg == false) { //make sure it's a boolean
                mainDroneObject.socket.send(JSON.stringify({
                    "type": "set",
                    "attributes": {
                        "armed": arg
                    }
                }))
            }
        },
        location : {
            //accepts argument in {lat:x, lon:x, alt:x, type:LocationGlobal,LocationGlobalRelative,etc} form
            home_location:function(arg){
                mainDroneObject.socket.send(JSON.stringify({
                    "type": "set",
                    "attributes": {
                        "location":{
                            "home":arg
                        }
                    }
                }))
            }
        },
        channels : {
            overrides : function(arg){
                mainDroneObject.socket.send(JSON.stringify({
                    "type": "set",
                    "attributes": {
                        "channels":{
                            "overrides":arg
                        }
                    }
                }))
            }
        }
        
    }
}
