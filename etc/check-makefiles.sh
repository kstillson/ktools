#!/bin/bash

# TODO: dont think this works anymore; outputs too much; needs fixing...

# Check to see if any files that look like source code files are present
# but missing from a Makefile target specification.

top_level_dir='ktools'

if [[ $(basename $(pwd)) != "$top_level_dir" ]]; then
    echo "please run from the $top_level_dir dir."
    exit -1
fi

temp_files_found="/tmp/files_found"
temp_targets_found="/tmp/targets_found"
temp_targets_missing="/tmp/targets_missing"

dirs_with_makefiles=$(ls -1 */Makefile | cut -d/ -f1)
for dir in $dirs_with_makefiles; do
    find $dir -type f -print | cut -d/ -f2- | egrep -v 'Makefile|\.md$|test_|testdata' | cut -d. -f1 | sort > $temp_files_found
    makefile="$dir/Makefile"
    egrep '_TARGETS :?=' $makefile | sed -e 's/#.*$//' | cut -d= -f2- | tr ' ' '\n' | cut -d. -f1 | sed -e '/^$/d' | sort > $temp_targets_found
    cat $temp_files_found | fgrep -v -f $temp_targets_found > $temp_targets_missing
    echo ""
    if [[ -s $temp_targets_missing ]]; then
	echo "$dir - files missing from Makefile targets:"
	cat $temp_targets_missing
    else
	echo "$dir - ok"
    fi
done

echo ""
# rm $temp_files_found $temp_targets_found $temp_targets_missing
exit 0
