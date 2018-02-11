# DroneKitHTTP
WebSockets API for ArduCopter and other MAVLink vehicles compatible with 3DR DroneKit

This project is still very much a work in progress, but it aims to be a simple way to manipulate an ArduCopter drone (in my case a 3DR Solo) from a simple client-side JavaScript app.

### Why would you want this?

My use case is fairly broad, but I want to be able to make small web apps that I can host on a web server on the drone's controller (a Linux machine) that will allow any smartphone or tablet to control attributes of the drone.

My first thought was gimbal control, as this would allow a dual-operator mode that's normally only found on $3K+ drones. However it also opens up possibilities for a "trainer" mode, and basically any other idea you can come up with.

### Isn't this dangerous?

Yes, if misused. The API is designed with the hope that any client-side app would prompt the user for a password rather than storing the password in the client-side code like an API key. API clients cannot even read attributes of the drone without authentication, and passwords are stored and transferred securely with salted sha256 hashes. It's not _perfect_ security, but the MAVLink protocol itself has no security whatsoever, so the risk of someone cracking the password to the drone's WiFi network is much greater than the risk of someone being able to find an obscure exploit in this API.

But, with that said, if you use the API it's likely to cause bodily harm, explosions, and billions in property damage. So don't use the API, or at least don't hold me responsible.

### How do I use it?

Right now the documentation is pretty nonexistent since I am still writing the API, but you can look at the ``reference.md`` file for some simple examples of packets, or look at the DemoPage example app to see a simple JS library developed around this API.

I hope to improve the documentation and overall usability of this API soon, but for now it is just a fun project and still under development. Enjoy!
