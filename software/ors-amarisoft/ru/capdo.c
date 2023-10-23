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

// `capdo prog ...` executes prog with inherited capabilities.
// It is used as trampoline to run script under setcap environment.

#include <errno.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <sys/capability.h>
#include <sys/prctl.h>

static int die(const char *fmt, ...);
static int die_err(const char *msg);

int main(int argc, const char *argv[]) {
    cap_t caps;
    cap_value_t cap;
    cap_flag_value_t flag;
    uint64_t capbits = 0;

    if (argc < 2)
        die("usage: capdo prog arguments...");

    // permitted -> inheritable  (so that we can raise ambient)
    caps = cap_get_proc();
    if (!caps)
        die("cap_get_proc failed");
    for (cap = 0; cap < CAP_LAST_CAP; cap++) {
        if (cap_get_flag(caps, cap, CAP_PERMITTED, &flag)) {
            if (errno = EINVAL)
                continue; // this cap is not supported by running kernel
            die_err("cap_get_flag");
        }
        if (flag) {
            cap_set_flag(caps, CAP_INHERITABLE, 1, &cap, flag)  && die_err("cap_set_flag");
            capbits |= (1ULL << cap);
        }
    }
    cap_set_proc(caps) && die_err("cap_set_proc");

    // raise ambient capabities to what is permitted/inheritable
    for (cap = 0; cap <= CAP_LAST_CAP; cap++) {
        if (capbits & (1ULL << cap))
            prctl(PR_CAP_AMBIENT, PR_CAP_AMBIENT_RAISE, cap, 0, 0)  && die_err("prctl ambient raise");
    }

    // tail to exec target
    argv++;
    execv(argv[0], argv);

    // the only chance we are here is due to exec error
    die_err(argv[0]);
}

static int die(const char* fmt, ...) {
    va_list ap;

    fprintf(stderr, "E: capdo: ");

    va_start(ap, fmt);
    vfprintf(stderr, fmt, ap);
    va_end(ap);

    fprintf(stderr, "\n");
    exit(128);
    return 0;
}

static int die_err(const char* msg) {
    return die("%s: %s", msg, strerror(errno));
}
