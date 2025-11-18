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

    fprintf(stdout, "CRASH_TYPE:timeout|SIGNAL:%d", signal);
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

        char outbuf[BUFFER_LEN];
        char errbuf[BUFFER_LEN];
        // tracer loop
        while (WIFSTOPPED(status)) {
            // capture binary/child stdout
            ssize_t n;
            while ((n = read(stdout_pipe[0], outbuf, BUFFER_LEN)) > 0) {
                write(STDOUT_FILENO, "STDOUT:", 7);
                write(STDOUT_FILENO, outbuf, n);
            }

            // capture binary/child stderr
            while ((n = read(stderr_pipe[0], errbuf, BUFFER_LEN)) > 0) {
                write(STDERR_FILENO, "STDERR:", 7);
                write(STDERR_FILENO, errbuf, n);
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

        write(STDOUT_FILENO, "|", 1);
        write(STDERR_FILENO, "|", 1);

        // disable queued timeout
        alarm(0);

        // record results for crash handler to analyse
        if (WIFSIGNALED(status) || (WIFSTOPPED(status) && WSTOPSIG(status) != SIGTRAP)) {
            int signal = WIFSIGNALED(status) ? WTERMSIG(status) : WSTOPSIG(status);
            fprintf(stdout, "CRASH_TYPE:crash|SIGNAL:%d", signal);
        } else {
            fprintf(stdout, "CRASH_TYPE:none|signal:0");
        }

        // record the coverage results
        fprintf(stdout, "|coverage:");
        bool first_cov = true;
        for (int i = 0; i < MAX_COVERAGE_SIZE; i++) {
            if (coverage_bitmap[i]) {
                if (!first_cov) {
                    fprintf(stdout, ",");
                    first_cov = false;
                }
                fprintf(stdout, "%x", i);
            }
        }

    }

    return 0;
}
