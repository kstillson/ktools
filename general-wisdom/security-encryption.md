
# Encryption

I like encryption.
It's a dangerous tool, but hey- why should *we* fear to use it?


## Transparent encryption

In olden days, you'd have an encrypted file (or partition), you'd run a tool
to decrypt it, thus creating a plain-text file (and requiring double the
space, at least temporarily).  You'd do whatever you need to with the
plain-text data, and then, if you've made changes, run a tool to re-encrypt
it.  And then you have to remember to delete the plain-text version.  And as
"deleting" is often possible to undo, you often have to use some other tool to
carefully wipe the plain-text data in a way where undelete won't work.

Transparent encryption replaces all that with a much easier-to-use mechanism.

With TE, you have an encrypted directory, and when you run a tool, and it
creates a virtual directory, which provides a decrypted view into the
encrypted folder.  As you read or write things in the virtual directory, the
TE system performs the necessary encryption and decryption in-line and in
real-time, and without creating separate copies of the plain-text data.  When
you're done, the TE system just turns off the virtual directory mapping, and
everything is automatically secure again.

This is so quick and easy to use, that it pretty much makes sense to have all
your data files encrypted all the time, and to use TE to access them only when
you actually need access.

The Linux kernel actually has a TE system built-in.  The user-space tool that
allows you to mount encrypted directories is available in the Debian/Ubuntu
package ecryptfs-utils.  For a while, Ubuntu had the option to encrypting your
entire user home directory, and using PAM to auto-mount the TE decryption of
it when you log in.  This was removed for vaguely described "security
reasons," but the tool to manually mount things is still easily available.

Personally, I tend to use a slightly older TE system called "encfs."  It also
has some vague warnings that security researches found flaws in it, but from
what few technical details I've been able to find, the attacks sound like they
require some pretty special circumstances to pull off, and I so much prefer
the tooling and interface for encfs that I use it anyway.


### Data separation

It's worth pointing out that if you have a system which automatically mounts
your TE whenever you log in, and you're always logged in, then your encrypted
data is visible to any hacker who manages to get access to your user-id at
basically any time.

A better practice is to break your data into different sections, using
different decryption passwords, and only mount the section you need at any
particular time.  And of course, try to keep your high-value data in different
sections that your commonly-mounted data.


## Server-side vs. client-side

So here's a question: you've got a server that stores most of your data, and
the client machine where you use most of your data is a different machine.
Should you perform the TE on the server-side or the client-side?

My answer is that you should do it on the client side.  The server is
generally oblivious to whether its serving encrypted or plain-text data; it
works the same way (at least assuming the TE is using efficient fixed-block
random I/O, which I believe all of them do).  Furthermore, most TE's
(certainly encfs) don't mind if the encrypted data is itself coming from a
remote file-system.  In this way, even if the server is compromised, it
actually cannot share the plain-text data with the hackers; it never sees it.

This seems to me like an elegant separation of concerns- storage on the server,
and decryption on the client.

btw- I tend to use sshfs for mounting my remote filesystems.  Back in the day
it was kinda slow, but on a modern system, you have to be moving *a lot* of
bits before you'd even notice the difference.

So in-other-worse, I use sshfs to mount the encrypted data onto the client
machine, then use encfs on the client machine to create my plain-text virtual
directory.


## Automation / Keymaster

With all this layering of mounted virtual decryption on-top of mounted remote
filesystems, it probably won't surprise you to learn that I've got a helper
script that knows all my various encrypted directories, and their various
dependencies, and can follow dependency chains and run all the necessary
commands to establish the multi-level mounts.

Naturally my ssh private key has a password on it, but I do use the Ubuntu
ssh-agent to keep that in memory for a while after being entered, so I don't
have to type it several times if requesting a complicated mount.

In addition, I have some of my TE encryption password stored in my
[keymaster](../services/keymaster) instance, and the mounting script knows
how to retrieve and use them.  Worth noting though- I do not keep the
passwords for my most sensitive encryption directories stored anywhere.  They
must be manually entered, no agent is allowed to cache them, and various
automated systems continuously check if it looks like I'm done using those
most sensitive files, and if so, automatically un-mount the TE.

Obviously it's up to you to balance your own convenience-vs-security.

