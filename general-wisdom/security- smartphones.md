
# Smart phone security

Smartphones are really handy.  For you, and for everyone who wants to violate
your security and your privacy.

The security model for smartphones has come a long way in the last few years,
but I still really don't trust it.  I've just been to too many Defcon security
conferences where the speaker happily announces that every phone that
auto-connected to their Wifi access point or the femtocell they've set up is
now totally hacked.

So...

- *Never* do security critical operations like banking on your phone.  It's
   convenient up until the time your bank account is p'wned, and then it's
   very inconvenient.

- *Strongly resist* the pressure from everyone and their uncle to install
   their custom app.  Apps get way too much access to the phone's platform and
   potentially to other app's data.  Ask yourself- is there a reason they
   can't provide this functionality with a traditional website?  If you can't
   think of a good reason, then be very suspcious of why they think you need
   an app.  If you're forced to install an app, uninstall it as soon as the
   compelling reason for it goes away.

- Whenever asked to enter credentials into a phone, think about how you would
  recover if they were stolen.  For a lot of uses, this is actually a
  reasonably happy story.  For example, when entering Google account
  credentials, your very-power password is immediately exchanged for a much
  less powerful access token.  That token can do lots of things, like read and
  send email.  But there are a lot of things it cannot do -- it cannot change
  your password, and it cannot cancel other access tokens.  If you log into
  Google from somewhere else (e.g. a real computer), and go account ->
  security -> my devices, you can find the phone and cancel it's access token.
  And as soon as that's done, the phone loses all access to your account and
  can't get it back without the password.  This is actually a reasonably well
  thought-through system.  Whenever you're asked to enter credentials into a
  phone, especially a custom app from a company you don't believe will have
  hired world-class security experts for their app development, ask yourself
  if there's as good a story about how to recover from a breach.

