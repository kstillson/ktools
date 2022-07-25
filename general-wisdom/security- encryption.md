
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

@@



## Server-side vs. client-side


## Keymaster

