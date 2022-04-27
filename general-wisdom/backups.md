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

    + Unexpected change detection: An automated system should compare
      recent versions of files and detect unexpected patterns of changes.
      For example: large numbers of files changing simultaneously (other
      than system binaries during an upgrade), or particular key files that
      are never expected to change suddently changing.

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

      + Pull the data using an unpriledged account and use tools like Linux
        capabilities to allow bypassing access controls for reads only.

    + When using a mechnaism where each system pushes to a central serer:
    
      + Push the data to a holding area.  The backup system can then inspect
        the holding area submission and decide whether to accept it and where
        to put it.  *Critically,* the system pushing its data must not be able
        to disrurb versions of the backup other than "most recent."  Failure
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
        encryptied and you've got multiple users with separate keys, this
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
    you rely on at-rest encrpytion for your primary data (rather than
    encrypting it at the time of backup), then you'll need a separate solution
    for this cloud-based data-- ideally pulling it into an encrypted-at-rest
    archive.


## My solution

TODO

### step 1: Cloud pull

I use "rclone" to pull my data from cloud storage and store it in my
primary storage.  The rclone configuration is encrypted so it doesn't risk
leaking cloud credentials when it is backed up.  The retireved data is
stored into an encrypted directory so its safe when sent to remote
backups.  Both the rclone and storage passwords are retrieved using
keymaster (TODO: link), and the whole process is wrapped in a docker
container that's launched by cron on main server.

I check how many photos have been modified in the last 30 days, and raise
an alert if it's zero, and monitor the last-change date of a file in Google
drive that I modified all the time, and make sure it's not too old.


### rsnapshot: versioned local

rsnapshot (TODO: link) 


rsnapshot: versioned local pull with caps and change detection; quick and
east restore.  backed up log age test

### Rclone push to remote

rclone: schedule offset push to a distant commerical service (latest only)
for regional threats.  copy back test 


### Manual backup #1

manual backup 1: rsync of versioned data with offset schedule, 2 distinct
drives, one in local safe, one in nearby safe


### Manual backup #2

manual backup 2: alternate encryption

