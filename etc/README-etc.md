
# etc dir

This directory contains a grab-bag of items, mostly internals used by the
build system.

There are several Makefile-* files, which are essentially common library
Makefile content that are imported into the other real Makefile's throughout
the system.

There are also several .py and .sh helper scripts that perform operations too
complex to easily code up in Makefile recipes.

And there are several .template files that contain starter content for
configuration files that will be copied into position and offered up for
editing by the :prep target of the top-level Makefile.

The graphviz subdirectory contains the .dot source code and generated
graphical elements used in various markdown files.

And the make process will also store various build-status stamp files in this
directory, which are .gitignore'd and can be purged with a "make clean".

