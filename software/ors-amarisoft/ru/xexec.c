// Copyright (C) 2023  Nexedi SA and Contributors.
//
// This program is free software: you can Use, Study, Modify and Redistribute
// it under the terms of the GNU General Public License version 3, or (at your
// option) any later version, as published by the Free Software Foundation.
//
// You can also Link and Combine this program with other software covered by
// the terms of any of the Free Software licenses or any of the Open Source
// Initiative approved licenses and Convey the resulting work. Corresponding
// source of such a combination shall include the source code for all other
// software used.
//
// This program is distributed WITHOUT ANY WARRANTY; without even the implied
// warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
//
// See COPYING file for full licensing terms.
// See https://www.nexedi.com/licensing for rationale and options.

// Program xexec does what exec in shell does but as standalone program.
// It is used as trampoline to run a script under setcap environment.

#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>


int main(int argc, const char *argv) {
    if (argc < 2) {
        fprintf(stderr, "E: usage: xexec prog arguments...\n");
        exit(128);
    }

    argv++;

    execv(argv[0], argv);

    // the only chance we are here is due to error
    fprintf(stderr, "xexec: %s: %s\n", argv[0], strerror(errno));
    exit(128);
}
