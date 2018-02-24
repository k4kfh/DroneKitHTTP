BuddyBox = {
    gamepad : {
        lastStartState : false
    },
    intervals : {
        gamepadMonitor : null,
        droneLink : null,
    },
    enabled : false, // nothing should edit this directly
    set : function(enable) { //call with true or false
        if (enable){
            BuddyBox.enabled = true
            BuddyBox.ui.overridesIndicator(true)
        }
        else {
            BuddyBox.enabled = false
            vehicle.set.channels.overrides({})
            BuddyBox.ui.overridesIndicator(false)
        }
    },
    ui : {
        ardupilot : {
            //Call with number
            // 0 means no usable connection to API
            // 1 means connected to API, but API lost drone
            // 2 means all is good
            connection : function(connState){
                var el = $("#ardupilot_connection")
                if (connState == 0){
                    // No connection to nothing, turn red and show "disconnected"
                    el.removeClass("orange green")
                    el.addClass("red")
                    el.html("Disconnected")
                }
                else if (connState == 1){
                    // Connection to API, but not drone, turn orange and say "RC Error"
                    el.removeClass("red green")
                    el.addClass("orange")
                    el.html("RC Error!")
                }
                else if (connState == 2){
                    // All is good, turn green and say "connected"
                    el.removeClass("orange red")
                    el.addClass("green")
                    el.html("Connected")
                }
            }
        },
        gamepad : {
            //call with 0 or 2 to indicate connection status
            connection : function(connState){
                var el = $("#gamepad_connection")
                if (connState == 0){
                    // No connection to nothing, turn red and show "disconnected"
                    el.removeClass("green")
                    el.addClass("red")
                    el.html("Disconnected")
                }
                else if (connState == 2){
                    // All is good, turn green and say "connected"
                    el.removeClass("red")
                    el.addClass("green")
                    el.html("Connected")
                }
            }
        },
        overridesIndicator : function(arg){
            var el = $("#disable_overrides_btn")
            var el2 = $("#gamepad_override")
            if (arg == true){
                //if overrides are enabled
                el.removeClass("grey z-depth-0")
                el.addClass("orange z-depth-3")
                el2.addClass("orange white-text")
                el2.html("Override Active")
            }
            else if (arg == false){
                el.removeClass("orange z-depth-3")
                el.addClass("grey z-depth-0")
                el2.removeClass("orange white-text")
                el2.html("Override Inactive")
            }
        }
    }
}

window.addEventListener("gamepaddisconnected", function(e) {
    BuddyBox.set(false)
    BuddyBox.ui.gamepad.connection(0)
});

window.addEventListener("gamepadconnected", function(e) {
    BuddyBox.ui.gamepad.connection(2)
});

$( document ).ready(function() {
    vehicle = new Drone("ws://localhost:8080/websocket", 500, "BigHotelWithTheLightOn", function (e) {}, function () {
        alert("Password refused! No API access.")
    })
    
    //This interval regularly sends any necessary override info to the drone
    BuddyBox.intervals.droneLink = setInterval(function(){
        //code to send overrides
        var gamepad = navigator.getGamepads()[0] //use the first gamepad that appears
        var channelOverrides = {
            1 : Math.round((gamepad.axes[2]+2)*500+500), //roll
            2 : Math.round((gamepad.axes[3]+2)*500+500), //pitch
            3 : Math.round((gamepad.axes[1]*-1+2)*500+500), //throttle INVERT
            4 : Math.round((gamepad.axes[0]+2)*500+500), //yaw
        }
        
        
        if (BuddyBox.enabled){
            vehicle.set.channels.overrides(channelOverrides)
        }
        
        //Process drone connection indicator
        if (vehicle.vehicle.connected == true) {
            //everything is cool bruh
            BuddyBox.ui.ardupilot.connection(2)
        }
        else if (vehicle.socket.readyState != 1) {
            //we're not even connected to the API
            BuddyBox.ui.ardupilot.connection(0)
        }
        else if (vehicle.socket.readyState == 1 && vehicle.vehicle.connected == false){
            //if we're connected to the API but the API isn't connected to the drone
            BuddyBox.ui.ardupilot.connection(1)
            //disable the override here for safety
            BuddyBox.set(false)
        }
    }, 250)
    
    //This interval monitors the gamepad controls (it's much faster than the droneLink one because it has to be)
    BuddyBox.intervals.gamepadMonitor = setInterval(function(){
        var gamepad = navigator.getGamepads()[0] //use the first gamepad that appears
        // toggle logic for override status
        if (gamepad.buttons["9"].pressed && BuddyBox.gamepad.lastStartState != gamepad.buttons["9"].pressed){ //most of this is debouncing code
            if (BuddyBox.enabled == true){
                BuddyBox.set(false)
            }
            else{
                BuddyBox.set(true)
            }
        }
        BuddyBox.gamepad.lastStartState = gamepad.buttons["9"].pressed
        
        //display gamepad values as percent
        var channelOverrides = {
            1 : Math.round((gamepad.axes[2]+1)*50), //roll
            2 : Math.round(((gamepad.axes[3]*-1)+1)*50), //pitch
            3 : Math.round((gamepad.axes[1]*-1+1)*50), //throttle INVERT
            4 : Math.round((gamepad.axes[0]+1)*50), //yaw
        }
        
        $("#gamepad_roll").css("width", channelOverrides["1"] + "%")
        $("#gamepad_pitch").css("width", channelOverrides["2"] + "%")
        $("#gamepad_throttle").css("width", channelOverrides["3"] + "%")
        $("#gamepad_yaw").css("width", channelOverrides["4"] + "%")
        
        //print vehicle values with jquery
        var apmChannels = {
            "1":Math.round((vehicle.vehicle.attributes.channels["1"]-1000)/10),
            "2":Math.round((vehicle.vehicle.attributes.channels["2"]-1000)/10),
            "3":Math.round((vehicle.vehicle.attributes.channels["3"]-1000)/10),
            "4":Math.round((vehicle.vehicle.attributes.channels["4"]-1000)/10),
        }
        $("#ardupilot_roll").css("width", apmChannels["1"] + "%")
        $("#ardupilot_pitch").css("width", apmChannels["2"] + "%")
        $("#ardupilot_throttle").css("width", apmChannels["3"] + "%")
        $("#ardupilot_yaw").css("width", apmChannels["4"] + "%")
        
        //print flight mode
        $("#ardupilot_mode").html(vehicle.vehicle.attributes.mode)
        
        //see if any flight mode buttons are pressed
        if(gamepad.buttons[0].pressed == true){ //if A pressed, LOITER
            vehicle.set.mode("LOITER")
        }
        else if(gamepad.buttons[1].pressed == true){ //if B pressed, BRAKE
            vehicle.set.mode("BRAKE")
        }
        else if(gamepad.buttons[8].pressed == true){ //if BACK pressed, RTL
            vehicle.set.mode("RTL")
        }
    }, 20)
});