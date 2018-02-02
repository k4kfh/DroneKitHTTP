**Verify with Key/Secret Pair**
You must do this to gain API access.

- Request: ``{"type":"validate", "token":"this is where the hash would go. It's sha256(sha256(password)+randomSaltFromHelloMsg)"}``
- Reply: ``{"type":"validate", "status":true}``

**Set Attribute Listener**
This will send continuous updates about all the vehicle's attributes. 99% of the time you will want this. 4Hz is recommended update rate (this is where the 250ms comes from).

- Request: ``{"type":"get", "listener":250}``
- Reply (continuously resent): ```{
        "type":"return",
        "fromListener":True,
        "attributes"://attributes object
}```

**Set Editable Attribute**
- Request: ``{"type":"set", "attributes":{"armed":true}}``
- Reply: None (watch attributes object or whatever you set)
