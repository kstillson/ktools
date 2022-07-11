
TODO(doc)

standard make command		Docker equivalent
-------- ---- -------		------ ----------
make all                        d-build
make test                       ./Test -r
make install                    d-build --setlive

Note that if you want to do all the above in order, plus auto (re-)start the
container (if it has an "autostart" file), you can use the shortcut:
				d-build -a

