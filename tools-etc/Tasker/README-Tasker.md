
# Tasker exports

Tasker is an Android app that allows you to design scripts that run on your
phone using a graphical interface.  I've included exports of several of my
Tasker projects here.

The .xml file can be imported directly into Tasker.  You'll need to get the
file onto your phone somehow (I use Google Drive), and then move the XML file
into /internal storage/tasker/projects.  Once done, create a new project
(long-click the home icon in the lower left), then long click the new project
and select 'import'.

I've also provided a .desc file for each.  This is another Tasker-generated
export that contains a more human-friendly description of the way the app
works, but there doesn't seem to be a way to import it; at least not that I've
found.  Anyway, feel free to use this as a sort of easier-to-read description
of how it works, in-case you want to re-implement something similar yourself
and don't like the idea of importing a basically unreadable .xml file, which I
must admit, would make me nervous.


## Alarm

This is a gesture-based personal alarm.

If you shake your phone while the screen is on, and the phone is oriented
normally, the script locks your phone in a way that disables a
fingerprint-based unlock; you actually have the type the full password.  This
is a very quick and easy gesture if you're afraid your phone is about to be
taken away from you, and you want to make sure it's locked.

If you orient the phone face down (with the screen on, whether it's locked or
not), the phone plays a warning chime.  If you then shake it, it activates a
panic mode.  This (a) plays a really loud annoying siren sound, and (b) sends
a text messages to a list of phone-numbers you enter that explains that you've
activated your panic mode, and requests that the recipients call the police.
It also contains a link to your current GPS-provided location.


## BT_Mgr (Bluetooth manager)

I've never really trusted Bluetooth security.  I prefer to keep it turned off
when I'm not actively using it.  This little script automates that.

Specifically, if the phone has Bluetooth turned on, but not connected to
anything, then after 2 minutes, the script turns Bluetooth off.

You can easily enough turn it back on from the phone's control panel, and then
you have 2 minutes to connect to something, or off it goes again.


## Nagger  (who watches the watcher?)

I make extensive use of Nagios to monitor the health of my various systems.
The purpose of nagger is to monitor my Nagios instance, and give me feedback
on my phone if something looks amiss.  In this way, I'm not totally dependent
on Nagios being able to send emails when something is wrong (which it might
not be able to do, when something is wrong).

I originally used the Android aNag for this, but it's been having more and
more problems in recent Android releases, and it's been taking longer and
longer for the author to fix them.  So I figured I'd implement my own in
Tasker.

Basically, every 15 minutes, between 8am and 11pm, nagger will check the
output of my Nagios status summary CGI script (see ../pylib/tools/nag.py).  If
there's a problem, it plays a sound and displays a sticky notification (sticky
meaning that it must be manually dismissed, even if the underlying condition
goes away).

There's also an ability to play a chime on the hour, and a different chime on
the half-hour...  Unrelated to the Nagios checks, but I was already running a
script at this times, so I threw it in here.

You can temporarily pause everything by tapping the little color-status
circle, and toggle enabling the chimes by long-pressing the status circle.
There's a little counter of how many successful / unsuccessful checks have
been run, which you can reset by tapping on the counter.

If you create a 1x1 widget to launch the UI (task "Nag Show"), then the script
will also update the icon of that widget with a green forward arrow to show
the last check was ok, or a red backwards arrow to show an error.

Because Nagger considers it an error to be unable to contact the status CGI,
it can warn about something like a complete power or connectivity loss, which
obviously Nagios itself would not be able to.


## PB  (pushbullet)

The [homesec system](../services/homesec/ext.py) uses the Android service
"Push Bullet" to send push notifications of important events.  The Push Bullet
app works fine, but for certain messages, I want to make sure I don't miss it.

So the PB script looks at incoming Push Bullet content, and if certain
substrings are seen ("#i" to indicate important info, "#a" to indicate an
alert), will play a loud chime/alert sound to make sure I know there's an
important message to review.

