# Backups

## Threat-based Backup Strategy

Your backup plans should be organized around the set of threats you need to
defend from.  Here's the threats that drive my requirements:

  - Hardware failure: mass storage devices fail.  **always.** and often
    with little warning.  To defend from this, you want an *automated*
    backup to make sure very recent versions of your files are available at
    the random moment some critical storage fails.

  - Automation failure: automated systems stop working eventually.
    **always.** Underlying assumptions you didn't know you had change, and the
    system stops working.  To defend from this, you need some sort of test
    that will alert you when your automated backup system stops working.

  - Corruption / Ransomware: Through minor hardware issues, operator error, or
    malware, files can get corrupted.  Without careful planning, an automated
    backup system might overwrite your only remaining non-corrupted copies
    with a corrupted ones!  Defenses:

    + Versioned backups: Keep the last several versions of your files, so
      you can recover the most recent version before the corruption.

    + Unexpected change detection: An automated system should compare recent
      versions of files and detect unexpected patterns of changes.  For
      example: large numbers of files changing simultaneously (other than
      system binaries during an upgrade), or particular critical files that
      are ~never expected to change.

  - Fire / flood / theft / earthquake: Backups that are stored in the same
    building as their primary data don't protect from these threats.
    Furthermore, some of these issues can be regional.  You might want to
    keep one set of backups physically nearby to make restoration quicker
    and easier (especially if there is also a network outage), but at least
    one redundant set should be stored far away from the primaries.

  - Backup mechanisms as a security threat: Backup systems often don't
    receive as much security attention as primary systems, yet they often
    have powerful credentials that allow them to bypass access controls
    (because they need to back up files regardless of normal restrictions).
    Hackers know this, and will target backup systems.  Defenses:

    + Keep your backup server(s) separated from primary servers; run on
      physically distinct hardware if possible.  Minimize the backup server
      attack surface by running only the backup software there.  Do not share
      credentials or allow connections from normal operation machines without
      special security checks.  Even (especially) root on your most important
      primary server should not be able to access the backup machines!
    
    + When using a mechanism that pulls data from a central backup serer:

      + Pull the data using an unprivileged account and use tools like Linux
        capabilities to allow bypassing access controls for reads only.

    + When using a mechanism where each system pushes to a central serer:
    
      + Push the data to a holding area.  The backup system can then inspect
        the holding area submission and decide whether to accept it and where
        to put it.  *Critically,* the system pushing its data must not be able
        to disturb versions of the backup other than "most recent."  Failure
        to follow this rule allows a hacker on a primary system to destroy the
        data and all its backup versions just by attacking the main system.
  
  - Advanced hackers: No matter how careful your electronic defenses, a
    sufficiently advanced hacker can find their way through.  Defense?  In
    addition to all the automated backups, have an occasional manual backup
    that is made to hardware physically disconnected (e.g. kept in a safe)
    when you're not actively making the backup.

      + Create a system where some file is updated by the manual process,
        and an automated system will alert if the file has not been updated
        within the expected time window.  Manual processes frequently
        break-down, and automated reminders like this are easy.

      + For the really paranoid, have two offline drives in your safe, and
        alternate between them.  That is, it is *never* the case that the
        primary data and all the backups are electrically connected at the
        same time.  At least one copy is always disconnected in the safe.
  
  - Backup theft: With so many copies of your files floating around in so
    many places, you have to assume they could fall into the wrong hands.
    Encryption is your friend here.  See my notes on data encryption in the
    "general wisdom" section (TODO: link), but in summary: at least encrypt
    the data both in transit and on the backup medium.  But a better
    solution is to have the primary data encrypted to begin with.  Then you
    don't need to do anything special for backups or restorations.
  
  - Decryption failure: Encryption is great, but has several failure modes.
    Most commonly, people forget encryption passwords -- especially if
    they're special purpose (e.g. backup only) and seldom used.  But also,
    entire encryption mechanisms can stop working.  A solution?  Yet
    another copy of your backup data, but using an alternate backup
    mechanism and decryption pass-phrase.

      + To be useful, the original data must first be decrypted, then
        re-encrpyted with the different mechanism.  If your primary data is
        encrypted and you've got multiple users with separate keys, this
        process would represent a significant security risk in itself.
        You'll have to weight the pro's & con's of your situation.

  - Cloud data: More and more data is being stored in the Cloud- don't forget
    about it when doing backup planning.  Reputable companies already sync
    multiple copies of your data, so loss from hardware failure is unlikely,
    but you could still lose your data if you lose access to your account, or
    if cloud-aware malware corrupts it.  Personally, I worry about Google
    Drive, Google Photos, and Gmail, but think through your own, and have a
    plan for each!  Solution: use an automated system to create local copies
    of your cloud data.  Place it in your normal primary storage so it
    benefits from the versioned & encrypted backups above.  Remember that if
    you rely on at-rest encryption for your primary data (rather than
    encrypting it at the time of backup), then you'll need a separate solution
    for this cloud-based data-- ideally pulling it into an encrypted-at-rest
    archive.


## My solution

TODO

### step 1: Cloud pull

"rclone" is an excellent tool for syncronizing cloud and local data.  As with
most things, I run rclone inside a docker container -- although I don't run it
as a continuous service, rather starting it up on-demand via cron.

When pulling data from the cloud, I tend to store it into various places in my
primary server's /home directory.  This is so my cloud data will automatically
benefit from my versioned local backups (see below).  For some data, like my
Google Photos, I don't consider them sensitive, so they're pulled directly
into local files.  For more sensitive content such as Google Drive files, I
use encfs to syncronize against a transparently-encrypted folder (TODO: link).
This means the data is "encrypted at rest" in my local /home folder, so it
also gets the versioned backup, all safely encrypted.

Rclone needs my cloud credentials to perform the sync.  To keep those safe, I
use rclone's built-in capability to encrypt its configuration.  This means
rclone needs the configuration password to run, and of course the container
needs the encfs password to mount the encrypted folder.  Both of these are
pulled at run-time from keymaster (TODO: link) so no secrets need to be stored
in the docker source-code or crontab files, which makes them safe and easy to
back up.

As mentioned in monitoring (TODO: link), it's very important to have automated
tests that confirm that automated processes have worked.  I do this in two
ways: first, after running rclone, I check that file update times are as
expected.  For example, when syncing Google Photos, I found the number of
downloaded image files that have been created during the last 30 days.  I
always take at least one photo per month, so if the script doesn't see any, it
raises an alert- specifically causing the rclone docker container to exit with
a non-zero status, which should cause cron to send me an email.  However,
historically I've found cron sending emails isn't always reliable, so in
addition, I use filewatch (TODO: link) to make sure that several downloaded
files that I know change regularly are not unacceptably old.  Actually, I tend
to check that their rsnapshot (see below) versioned backups are
acceptably new- thus testing both the rclone and rsnapshot.

See the /etc/init file in the rclone container (TODO: link) for the place
where most of the magic happens.


### step 2: rsnapshot versioned local backups

#### rsnapshot in general

rsnapshot (TODO: link) is a wonderful tool for keeping versioned local
backups.  It does away with the concepts of incremental and differential
backups, and instead makes clever use of Linux filesystem hard-links.

A hard-link is just two-or-more directory entries that point to the same
storage space (inode) on disk.  The filesystem keeps a reference counter so it
knows to reclaim the space (i.e. delete the file) when the last reference is
removed.  This means you can have any number of "copies" of a file, but only
consume the storage for a single copy.

Rsnapshot is given a schedule of snapshots to keep- for example, a daily
snapshot for each of the last 7 days, a weekly snapshot for each of the last 4
weeks, and a monthly snapshot for each of the last several months.  When
rsnapshot makes these "copies," it uses hardlinks for all the files that have
not changed between snapshots.

This means you can have any number of snapshots and only need the amount of
space to store 1 copy of each version.  For files that never change,
additional snapshots are essentially "free" (other than the space needed for
the directory contents).  And each snapshot is complete and ready-to-use; you
don't need to go through a restoration process to "assemble" some combination
of differencial and incremental backups.


#### My rsnapshot configuration: security

My rsnapshot instance ssh's from the backup server to all the systems it needs
data from, i.e. I "pull" the data.  The connection logs into an unprivlidged
account, generally named "rsnap".  In-fact, rsnap is more restricted than most
accounts, using "rsh" as the account's shell, set so that "rsync" is the only
command it can run.

I use Linux capabilities to allow rsync to bypass normal read ACLs.
Specifically, I add the following to /etc/security/capability.conf:

cap_dac_read_search     rsnap

and also run this on each machine that provices backup data:

sbin/setcap cap_dac_read_search+ei /usr/bin/rsync

Linux capabilities require these two pieces to meet in order to work: i.e.,
only uid rsnap running /usr/bin/rsync gets the ability to bypass normal ACLs,
and only for read access.

Note that if the rsync binary gets updated, it tends to lose that "setcap"
marking.  Hence, after upgrades are run, I use "q's" "enable_rsnap" to make
sure the setcap is re-established.  (TODO: link)


#### My rsnapshot configuration: monitoring

All automated systems break eventually, and if you don't have some sort of
monitoring, you'll likely miss it.

Fortunately, Linux is full of files that change on a predictable schedule
(like log files that change nearly continuously), so it's easy to check that
files in the rsnapshot repository have the expected ages.  I use filewatch for
this.  (TODO: link)


In addition, I wrap my on-demand launch of rsnapshot in a script that also
runs a little script I wrote called "rsnap-diff" (TODO: link).  What this does
is generate a daily report of the files that have changed between today's and
yesterday's daily snapshots, after applying some filtering to remove things
that are changed all-the-time by normal automated processes.

I find it incredibly useful to review this -- obviously I can see the things I
deliberately changed the previous day, but I can also see the side-effects of
those changes, and any other unexpected changes.  If some Linux service
modifies it's own configuration (or some other packages's (!))- I'll see it.
If it happens regularly and I decide I don't care, I can add it to the filter.

Critically, if some sort of corruption starts to change data throughout my
system- for example, some malware starts encrypting things- it'll show up
here.  This allows me to pause automated snapshoting, to make sure the
automated system doesn't merry go on replacing useful snapshots with corrupted
ones - and figure out how to fix things before they get worse.

Obvuously one has to have a moderate amount of Linux experience to understand
what the various changing files are, and what they mean.  But given this,
rsnap-diff gives incredible insight into what's going -- and recall that
because all the backed up systems are having their data pulled to the central
backup server, this insight isn't just for one server, it's for all of them.



### step 3: Rclone push to remote

Rsnapshot's versioned backups are great, but because the backup server that
runs it is physically near to my primary servers, it doesn't provide
protection from threats against the entire site (fire, flood, theft, etc).

Rclone to the rescue again.  But this time, rather than pulling from the
cloud, I'm pushing to it.  There are various commercial providers that offer
Amazon-S3 compatible services, but at reduced cost (and with cost based only
on storage used, rather than complicated and difficult-to-predict things like
i/o counts).  I use one called "Wasabi". (TODO: link)

In this case, rclone pushes my most recent snapshot from rsnapshot (above).  I
do this because rsnapshot has already conveniently assembled data from all my
backed-up servers into one place.  I only sync the most recent snapshot
because S3 doesn't support hard-links, so trying to sync multiple snapshots
would miss the magic space savings of rsnapshot and be very expensive.  So
obviously I'm taking the risk that I won't need to restore from backups that
simultaneously require versioning and remote storage.  i.e. I can survive
encryption ransomware, and I can survive a flood- both at the same time would
be more of a problem..  Although see below.

As with the rclone pull, the I use an encrypted rclone configuration to protect
my cloud credentials, and keymaster to store the password for the config.

And as with the rclone pull, I have an automated test to make sure it's
worked.  Specifically, I have a file on my primary server that cron changes
regularly.  Rsnapshot copies that to the backup server, then rclone copies it
to my remote web storage.  Upon completion of the cloud push, the /etc/init
script for rclone copies this file back from the cloud to a holding directory,
and checks to see if it's matches the one back on the original primary server.
This esentially confirms that the whole flow is working as expecte.


### Step 4: Manual backup #1

In addition to all the automated mechanisms above, I want at least one copy of
my primary data physically offline at all times.  To accomplish this, I have
two removable hard-drives, one stored in an on-site safe, and one in a
friend's safe.  At regular intervals (every few weeks), I alternate between
the drives, connecting one of them to my backup server, and dumping the entire
versioned backup contents.  Rsync has a mode that preserves hard-links, so the
cleverness of rsnapshot isn't lost.  I never retrieve both of the offline
drives at the same time, so I always have at least one versioned backup
physically offline, even when it's alnerate is being updated.

The backup is triggered by running a script, which updates a log-file that is
used for nothing else.  In this way, the last-change time-stamp of the
log-file shows the last time the manual process was run.  This makes it
trivial for filewatch (TODO: link) to alert if the manual process is not
executed within the expected time-frame.


### Step 5: Manual backup #2

Truthfully, I can't really think of any realisitc scenarios where my ability
to decrypt encfs encrypted directories would stop working in a way that I
couldn't restore at least temporarily.  None-the-less, it occurred to me that
this whole fancy scheme has a single-point-of-failure: encfs.  Almost
everything is encrypted with it- both my backups and my "live" copies.

To aleviate this, whenever I'm pulling my offline drives for an update, I grab
one last drive.  This one yet one more copy of the primary data backup image,
but in each case where encfs was protecting data, it decrypts it and
re-encrypts it using ecryptfs; just so I have the same data, still encrypted,
but using an entirely separate mechanism.

As usual, keymaster holds the decrypt and encrypt keys so the process can be
automated once the external drive is physically connected, and a single-use
logfile allows filewatch to alert if the manual process isn't done on
schedule.

