
There's no Makefile here because Docker containers need to be built and tested
by root, and since I don't want to require the entire tree to be built by
root, I don't want the standard recursive Makefile to decent into this part.

standard make command		Docker equivalent
-------- ---- -------		------ ----------
make all                        d-build
make test                       ./Test -r
make install                    d-build --setlive

Note that if you want to do all the above in order, plus auto (re-)start the
container (if it has an "autostart" file), you can use the shortcut:
				d-build -a

