# Browser Security

## Motivation

An incredible percentage of penetrations start with a human browsing a
website, and having malicious content on that site compromise their browser.

The browser is a very inviting target for attackers- it's a large and
complicated piece of software which, at the direction of visited sites needs
to interact with many parts of the operating system, and which in regular use
processes security critical credentials and content.

There are countless attack modes long associated with browsers: cookie
stealing, logic injection, cross-site-request-forgery, on and on.  Browser are
dangerous.  But they're also necessary.

Fortunately, Linux has a number of capabilities that allow us to significant
reduce browser risk, with just a little configuration.


## Browser separation

One of the best security-defense tricks is to use different browsers for
different purposes.  For example, I identify the following uses as areas I
would like to keep separate from each other:

- Browsing to Google: I use a lot of Google web services: Gmail, Drive, etc.
  Google has integrated their services into a reasonably cohesive platform,
  and it would be difficult to separate these services from each other, even
  if I wanted to.  So I don't try.  But I do keep the collected set of
  Google services separate from EVERYTHING ELSE.  I have one browser that I
  use to connect to all Google services, and that's all it's for.

  IMPORTANT SECURITY NOTE: your email is one of your most security critical
  services, even if you don't think of it as such.  This is because the vast
  majority of web-services allow you to change your password using nothing
  more than an email-based confirmation.  If someone captures control of
  your email, they get all the other sites basically for free.

- Financial stuff: I have a separate browser instance used for banks,
  credit-cards, investing, etc.  I keep it closed all the time except when
  it's in use, and before opening it, I close all other browser instances
  (except the Google browser, which I generally need open because the
  financial institutions often send 2nd factor tokens via email).

- High value accounts: This is for sites that I generally trust, and that I
  use for some moderately important purpose.  Things like utility companies,
  etc.  Less valuable than the financial group, but important enough to
  separate from the general purpose browser.

- General browsing: This is for sites where I have low-value accounts, or
  where I'm just doing general-purpose exploring of places that I don't
  consider particularly risky.

- The "bad boy browser": Used for sites I'm moderately suspicious of, or
  just generally feel should be quarantined from everything else.


## Keeping separate browsers separate

So when I talk about using "separate browsers," what do I actually mean?

Well, actually they're all the same browser (Google Chrome), but which each
use-case running in a separate special-purpose Linux user id.

I don't mean that I need to log-out and log-in as a different user each time I
switch browsers.  That would be really inconvenient.  In Linux x-windows, you
can allow other local system uid's to run programs in your x-server's
instance.  So for example, my primary login is "ken".  My "bad-boy-browser"
uses the Linux uid "ken-bbb", and in ~ken/.profile, I have:
  /usr/bin/xhost +SI:localhost:ken-bbb

This means that ken-bbb can launch x-windows programs, and they show-up in
ken's interface.  Now, this isn't perfect separation, xhost activates the full
x-windows API, which includes a bunch of capabilities that could be used to
spy on keystrokes (which is part of why I almost never type in
[passwords](security-passwords.md).  But it is pretty good separation; ken-bbb
cannot look at or change the files in ~ken, and an attack through the
x-windows API would have to be very specialized.

I also run each browser instance under
[firejail](https://firejail.wordpress.com/), just to add another layer of
protection against any of the alternate-uid browsers being able to run or
persist malicious code that could figure out what I'm doing and perhaps
consider an x-windows specific attack.


### Keeping it convenient

I want to be able to launch my various browsers with very little added
overhead.  Here's how I accomplish that:

I use Ubuntu's custom keyboard short-cut system to create a keyboard
combination that runs:
  /usr/bin/sudo -u ken-bbb /home/ken-common/bin/run-chrome

I have an /etc/sudoers entry that allows NOPASSWD execution of this
particular command by uid/ken for each of the alternate uid's.  They have
read-only access to /home/ken-common.  The script basically just launches
Chrome under firejail.

The script also creates a lock file upon launching a browser, and removes it
when the browser closes.  Why?  I have a separate system that monitors for
processes running as the alternate uid's when no browser lock-file is active
for that uid.  This warns me if something unexpectedly persists beyond the
lifetime of the browser.

I also have a keyboard shortcut that uses sudo to run a (root) bash script
that moves files from all my alternate-uid's Downloads/ directories over to my
main uid, changes ownership to the main uid, and then opens the file browser
on the main uid's Downloads directory.  In this way, it's not inconvenient at
all to grab files downloaded by one of the specialized browser accounts.


### Audio

The x-windows API enabled by xhost does not permit audio to pass from one
Linux uid to another.  I fiddled around for a while to get this working, and
here's what I found...
[source](http://billauer.co.il/blog/2014/01/pa-multiple-users/)

For the account that wants to receive sound from others ("ken" in my case),
add the following to ~/.pulse/default.pa:
  load-module module-native-protocol-tcp auth-ip-acl=127.0.0.1

Then in the uid(s) you want to be able to send sound from:
  include "--whitelist=~/.pulse" in the firejail arguments,

and in the sender's ~/.pulse dir, create client.conf containing:
  default-server = 127.0.0.1
  enable-shm = no


## A note on credit

Some folks seem to consider credit card numbers to be a tremendous secret.  Do
I have rules about which browser instances I will provide credit card numbers
to?  No.

To me, one of the primary purposes of a credit card is to provide a flexible
barrier between ones money and the rest of the world.  Credit card companies
are pretty good at noticing and blocking unusual transactions, and either you
or the company can easily nix a card and issue a replacement.  And in my
experience, getting any successful fraudulent charges reversed is generally not
that difficult.

The fact that credit card numbers are so easily changed makes them a great
tool for using where there's limited trust between the parties.  What you
never want to do is share data which is difficult to change and directly tied
to your money supply- like your bank account and routing numbers.  I'm always
amazed that some companies have the gaul to ask for this, and I would
certainly never provide it.  In-fact, a top reason I would suggest that paying
online by credit card is *more secure* than printed checks is that checks
contain that valuable-and-difficult-to-change combination of account and
routing number, and in an unencrypted format with no mechanism for tracking
whether it's intercepted by unexpected parties in transit.

Once-upon-a-time, Citibank had a cool feature where you could create on-demand
virtual credit-card numbers attached to your real card only at the bank.  This
essentially permitted creation of a separate virtual card number for each
transaction, or at least for each vendor- each of which could be canceled
separately.  This not only minimized the annoyance of needing to cancel a
number, but also meant you got a pretty-darn-good lead on which vendor leaked
or abused your number.  I wish that caught on.

