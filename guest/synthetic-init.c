/*
 * G2.1 fixed-purpose synthetic Linux Guest init. No network, shell, packages,
 * login, executable user input or model integration.
 * --self-test runs the trusted parser on the build host; NOT a VM boot proof.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/types.h>
#include <unistd.h>

#define MARKER "FOUNDATION_GUEST_READY_V1 "
#define KEY "foundation.probe_token="
#define HEX_LEN 32
#define CMDLINE_CAP 4096

static bool is_hex(char c) {
    return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f');
}

static bool parse_token(const char *buf, size_t n, char out[HEX_LEN + 1]) {
    size_t pos = 0;
    unsigned matches = 0;
    const size_t key_len = sizeof(KEY) - 1;
    while (pos < n) {
        while (pos < n && (buf[pos] == ' ' || buf[pos] == '\n' || buf[pos] == '\t'))
            ++pos;
        if (pos == n) break;
        size_t start = pos;
        while (pos < n && buf[pos] != ' ' && buf[pos] != '\t' && buf[pos] != '\n')
            ++pos;
        size_t len = pos - start;
        if (len >= key_len && memcmp(buf + start, KEY, key_len) == 0) {
            if (len != key_len + HEX_LEN || ++matches != 1) return false;
            for (size_t i = 0; i < HEX_LEN; ++i) {
                char c = buf[start + key_len + i];
                if (!is_hex(c)) return false;
                out[i] = c;
            }
            out[HEX_LEN] = '\0';
        }
    }
    return matches == 1;
}

static int emit_ready(int fd, const char *token) {
    const char *parts[] = {MARKER, token, "\n"};
    const size_t lengths[] = {sizeof(MARKER) - 1, HEX_LEN, 1};
    for (size_t i = 0; i < 3; ++i) {
        size_t offset = 0;
        while (offset < lengths[i]) {
            ssize_t count = write(fd, parts[i] + offset, lengths[i] - offset);
            if (count < 0 && errno == EINTR) continue;
            if (count <= 0) return 1;
            offset += (size_t)count;
        }
    }
    return 0;
}

int main(int argc, char **argv) {
    char token[HEX_LEN + 1];
    if (argc == 3 && strcmp(argv[1], "--self-test") == 0) {
        const char *line = argv[2];
        if (strlen(line) >= CMDLINE_CAP || !parse_token(line, strlen(line), token))
            return 2;
        return emit_ready(STDOUT_FILENO, token);
    }
    if (argc != 1 || getpid() != 1) return 3;

    if (mount("proc", "/proc", "proc",
              MS_NOSUID | MS_NODEV | MS_NOEXEC, NULL) != 0)
        return 4;
    int in = open("/proc/cmdline", O_RDONLY | O_CLOEXEC);
    if (in < 0) return 5;
    char line[CMDLINE_CAP];
    ssize_t n = read(in, line, sizeof(line));
    close(in);
    if (n <= 0 || n >= (ssize_t)sizeof(line) ||
        !parse_token(line, (size_t)n, token))
        return 6;

    int console = open("/dev/console", O_WRONLY | O_NOCTTY | O_CLOEXEC);
    if (console < 0) return 7;
    int ok = emit_ready(console, token);
    close(console);
    if (ok != 0) return 8;
    for (;;) pause();
}
