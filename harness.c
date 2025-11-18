#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <unistd.h>
#include <sys/ptrace.h>
#include <sys/wait.h>
#include <signal.h>
#include <sys/user.h>
#include <fcntl.h>
#include <stdbool.h>

#define BUFFER_LEN 4096
#define MAX_COVERAGE_SIZE 65536

uint8_t coverage_bitmap[MAX_COVERAGE_SIZE];

pid_t child_pid = -1;

void add_coverage(uintptr_t addr) {
    uint32_t i = (uint32_t)(addr >> 4) & (MAX_COVERAGE_SIZE - 1);
    // mark address as visited in the bitmap
    coverage_bitmap[i] = 1;
}

void timeout_handler(int signal) {
    if (child_pid != -1) {
        // kill child process if still live
        kill(child_pid, SIGKILL);
    }
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <timeout_sec> <binary>\n", argv[0]);
        return 1;
    }

    int timeout_seconds = atoi(argv[1]);
    char *binary_path = argv[2];

    // create pipe to be able to redirect binary stdin/stdout/stderr and harness stdin/stdout/stderr
    int stdin_pipe[2];      // pipe[0] == write to binary, pipe[1] == read from harness
    int stdout_pipe[2];     // pipe[0] == read from binary, pipe[1] == write to harness stdout
    int stderr_pipe[2];     // pipe[0] == read child stderr, pipe[1] == write to harness stderr
    if (pipe(stdin_pipe) || pipe(stdout_pipe) || pipe(stderr_pipe)) {
        perror("pipe");
        return 1;
    }

    // create tracee process
    child_pid = fork();
    if (child_pid == -1) {
        perror("fork");
        return 1;
    }

    if (child_pid == 0) {
        // child process (will run the binary)

        // close unused pipe ends
        close(stdin_pipe[1]);
        close(stdout_pipe[0]);
        close(stderr_pipe[0]);

        // redirect stdio and close duplicate pipes (only need one)
        dup2(stdin_pipe[0], STDIN_FILENO);
        dup2(stdout_pipe[1], STDOUT_FILENO);
        dup2(stderr_pipe[1], STDERR_FILENO);
        close(stdin_pipe[0]);
        close(stdout_pipe[1]);
        close(stderr_pipe[1]);

        // allow parent to attach to process
        ptrace(PTRACE_TRACEME, 0, NULL, NULL);
        raise(SIGSTOP);

        // execute the binary with the input
        char *argv[] = {binary_path, NULL};
        execv(binary_path, argv);
        perror("execv");
        _exit(1);
    } else {
        // parent process (will run the tracer)
        int status;
        struct user_regs_struct regs;

        // close unused pipe ends
        close(stdin_pipe[0]);
        close(stdout_pipe[1]);
        close(stderr_pipe[1]);

        // set up a timeout
        signal(SIGALRM, timeout_handler);
        alarm(timeout_seconds);

        // input the stdin to the binary
        char buffer[BUFFER_LEN];
        ssize_t nbyte;
        while ((nbyte = read(STDIN_FILENO, buffer, BUFFER_LEN)) > 0) {
            if (write(stdin_pipe[1], buffer, nbyte) != nbyte) {
                // failed to write all of the input to program stdin
                break;
            }
        }

        // closing read end of pipe will signal EOF for the child process
        close(stdin_pipe[1]);
        waitpid(child_pid, &status, 0);

        // set pipes to nonblocking (so reads dont block ptrace loop)
        fcntl(stdout_pipe[0], F_SETFL, O_NONBLOCK);
        fcntl(stderr_pipe[0], F_SETFL, O_NONBLOCK);

        char *out = NULL;
        ssize_t out_len = 0;
        ssize_t out_cap = 0;
        char *err = NULL;
        ssize_t err_len = 0;
        ssize_t err_cap = 0;

        // tracer loop
        while (WIFSTOPPED(status)) {
            // capture binary/child stdout
            ssize_t n;
            char tmp[BUFFER_LEN];
            while ((n = read(stdout_pipe[0], tmp, BUFFER_LEN)) > 0) {
                if (out_len + n + 1 > out_cap) {
                    out_cap = (out_cap + n + 1) * 2 + 1024;
                    out = realloc(out, out_cap);
                }
                if (out) {
                    memcpy(out + out_len, tmp, n);
                    out_len += n;
                }
            }

            // capture binary/child stderr
            while ((n = read(stderr_pipe[0], tmp, BUFFER_LEN)) > 0) {
                if (err_len + n + 1 > err_cap) {
                    err_cap = (err_cap + n + 1) * 2 + 1024;
                    err = realloc(err, err_cap);
                }
                if (err) {
                    memcpy(err + err_len, tmp, n);
                    err_len += n;
                }
            }

            if (ptrace(PTRACE_GETREGS, child_pid, NULL, &regs) == -1) {
                // error tracing instruction
                break;
            }

            add_coverage(regs.rip);

            // go to next instruction
            // TODO: this is really slow, look into how i can optimise this
            if (ptrace(PTRACE_SINGLESTEP, child_pid, NULL, NULL) == -1) {
                // error executing next step
                break;
            }
            waitpid(child_pid, &status, 0);

            // check if child proc stopped by something other than a trap (i.e. crash)
            if (WIFSTOPPED(status) && WSTOPSIG(status) != SIGTRAP) {
                break;
            }
        }

        if (out) {
            out[out_len] = '\0';
            fprintf(stdout, "STDOUT:%s|", out);
            free(out);
        }

        if (err) {
            err[err_len] = '\0';
            fprintf(stdout, "STDERR:%s|", err);
            free(err);
        }

        // disable queued timeout
        alarm(0);

        // record results for crash handler to analyse
        if (WIFSIGNALED(status)) {
            int sig = WTERMSIG(status);
            if(sig == SIGKILL) {
                fprintf(stdout, "CRASH_TYPE:timeout|SIGNAL:%d", sig);
            } else {
                fprintf(stdout, "CRASH_TYPE:crash|SIGNAL:%d", sig);
            }
        } else {
            fprintf(stdout, "CRASH_TYPE:none|SIGNAL:0");
        }

        // record the coverage results
        fprintf(stdout, "|COVERAGE:");
        bool first_cov = true;
        for (int i = 0; i < MAX_COVERAGE_SIZE; i++) {
            if (coverage_bitmap[i]) {
                if (!first_cov) {
                    fprintf(stdout, ",");
                }
                fprintf(stdout, "%x", i);
                first_cov = false;
            }
        }

    }

    return 0;
}
