# Passwords

Passwords aren't great.  Well, specifically, passwords that humans try to
remember and type in all the time aren't great.  There's an impossible tension
between the need for long, complex, and different-for-every-system passwords,
and ones that you can remember and aren't too annoying to type in.

Fortuntely, there are a few tricks that can really help, until technology
moves on to alternative authentication mechanisms.


## Anti-pattern:  Password Reuse

Using the same password on multiple sites certainly cuts down on the number of
passwords you need to remember.  But, it also means that the security of the
most important site is no better than the security of the least important
site.

Keep this in mind -- that blog you created an account for, which is run by a
teenager with no security training or common sense has access to all the other
sites where you use the same password.  Never-mind how easy it is for hackers
to grab the blog's password database, what about the operator himself?!

No, you really need to use different passwords on every site.


## User-id variation

Before I go into ways to vary your passwords, let me also introduce the idea
of varying your username, especially when that username is an email address.
The baddies can't even try to see if your passwords are reusable if they can't
map between your usernames on different sites.

Systems like Gmail provide an essentially infinite number of email address
that all route to the same account, but look like different address.  For
example, if your account is name@gmail.com, then name+x1@gmail.com and
name+x2@gmail.com, etc, all route to your account.  You can put whatever you
want after the "+"; Gmail just sort-of ignores it.

If when you're dealing with AT&T, you use name+att@gmail.com, and when you're
dealing with the New York Times you use name+nyt@gmai.com, then you
effectively have a different username for every site on the Internet.  As a
side-benefit, when you receive spam, you can determine which business it was
that leaked your address, just by checking the address the mail was sent to.

Unfortunately, many websites don't allow "+"'s in account names, which does
defeat this approach.  However, many email services have configurable email
routing rules, which allow you to establish things like prefix-patterns that
would allow you to use "-", or some other character, instead of "+".  Google
"Workspaces" has this, for example.


## Password Formulas

A simple but really effective trick to solve the password reuse problem is:
rather than using the same password for multiple sites, use the same password
formula for multiple sites, and have the site name be one of the inputs to the
formula.

Here's an example:

    qWe974${L}${T}${F}__Z

where:
    ${L} is the last two characters of the site's address
    ${T} is the type of site.  W for web, B for banking, S for shopping, etc.
    ${F} is the first two characters of the site's address, reversed

So the password for gmail.com would be:   qWe974ilWmg__Z

That is a really strong password, and which will be sufficiently different for
every site that even a reasonably bright human would have to collect 4 or 5
known-site samples before they could figure out the pattern.

The password has mixed case, mixed alpha and numerics, and several special
characters (but not the ones that tend to get passwords rejected).  And it's
reasonably long as passwords go.  And after you've constructed passwords with
this formula a few times, it will be so second nature, you barely have to
think about it at all.

Btw, I do actually recommend folks have several different formulas.  For
example, one for work, one for really important sites (financial, etc), and
one for lower-priority general use.


## Password Managers

I like password managers (PMs), although I don't like trusting them
completely.

There are several things they're good at.  First, a PM is less likely to be
fooled than a human into offering up a password to a site who's domain looks
like another one, but isn't.  A careless click could take you to goog1e.com
(the number "1" instead of the "L").  That could easily enough trick you, but
wouldn't trick a PM.

Second, lots of password interception techniques work by spying on your
keyboard.  PMs avoid you typing in the most important things.

Third, PMs encourage you to use passwords longer than you would normally be
comfortable typing in.

The main problem with PMs is that they are very obvious and very juicy targets
for hackers.  Clearly you want one that does all the encryption locally- a PM
that does centralized encrpytion presents a prize where a single hack gets a
huge number of passwords; very bad.  But one still has to worry that with
something like a self-updating browser extension, a single hack to the code
repository could push an update that sends all your decrypted passwords to the
attackers.

So...

### PM mitigation 1: incomplete data

Here's a fun trick...  Go ahead and give your PM your secrets, but leave a few
characters off.  For example, don't tell it the "__Z" suffix.  Type that in
manually.  Now, even if your PM is breached, the hackers don't get complete
passwords, and chances are a few unsuccessful attempts will lock them out or
frustrate them sufficiently that they'll move on to the next target.

The main downside of this is that most PMs will see the difference between the
final password and the one it populated, and ask if you want to update it's
database.  Obviously with this technique you don't want to, and it's annoying
to have to do that extra click on each login.  So many only use this technique
for your most valuable sites, to minimize the inconvenience.


### PM mitigation 2: browser separation

If you're going to use a PM, *please* read my other file on separating
browsers by context [TODO: link].  You do not want your passwords for
low-value sites to exist in the same PM as your critically important ones.

In-fact, ideally, you should keep your critical sites browser closed and it's
PM logged out except when actually in use.  And you should close any
low-security browsers (which should ideally automatically log out of their
PMs), before you even open a high-security browser.  You just want to minimize
any chance of interaction between highly different security levels.


## Biometrics

So here's an idea -- let's use a password that you can't change, and which you
leave a copy of on every object you touch (or every high-rez camera you walk
by, etc).  No..  Biometric authentication isn't a great idea.  Perhaps someday
technology will evolove sufficiently that it can scan things that are hard to
intercept or make clones of, but it's not there yet.

I don't mind too much the idea of using a fingerprint to unlock your phone.
That's something you do very frequently (so the value of a rapid unlock is
increased), and where it is reasonably easy to cancel your phone's credentials
from remote should it fall out of your hands.  But see my thoughts on
smartphone security [TODO: link]; the main reason I'm willing to accept this
risk is that I consider smartphones to be incredibly vulnerable and I don't
put much of value on them to begin with.
