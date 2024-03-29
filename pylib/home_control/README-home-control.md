
# home-control: smart-home CLI and web service

home_control ("hc") can be used as a Python library, stand alone command,
wrapped into a web service, or a Docker-based micro-service.  Examples of each
of these are provided.

HC supports arbitrarily complex scenes, i.e. multiple devices reacting in
different ways to a single command.  Scenes can include other scenes, which
allows constructing complex arrangements elegantly and with little repetition
even when some elements are shared between scenes.  By default devices are
contacted concurrently, which can give a nice dramatic effect when changing
lots of lights at the same time.  Scenes can also contain delayed actions,
i.e. sequences of events triggered by a single scene command.

HC uses a plug-in based mechanism to control actual external hardware devices.
Currently plug-ins are provided for TPLink switches, plugs, and smart-bulbs
(as this is primarily what the author uses), and for sending web-based
commands.  Additional plug-ins are reasonably easy to write, and hopefully
more will come along over time.

Why TPLink?  Besides having reasonable reliability and cost, TPLink modules
have a local server that allows manipulation and querying via local network
HTTP.  i.e. you can control them from your own systems without needing to
depend on cloud integration.

