#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <unistd.h>
#include <sys/ptrace.h>
#include <sys/wait.h>
#include <signal.h>
#include <sys/user.h>

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

    fprintf(stdout, "crash_type:timeout|signal:%d\n", signal);
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <timeout_sec> <binary>\n", argv[0]);
        return 1;
    }

    int timeout_seconds = atoi(argv[1]);
    char *binary_path = argv[2];

    // create pipe to be able to redirect binary stdin
    int proc_pipe[2];
    if (pipe(proc_pipe) == -1) {
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

        // close write end of pipe (we only care about read end)
        close(proc_pipe[1]);
        // redirect stdin to read from pipe
        dup2(proc_pipe[0], STDIN_FILENO);
        close(proc_pipe[0]);

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

        // parent proc will only be writing
        close(proc_pipe[0]);

        // set up a timeout
        signal(SIGALRM, timeout_handler);
        alarm(timeout_seconds);

        // input the stdin to the binary
        char buffer[BUFFER_LEN];
        ssize_t nbyte;
        while ((nbyte = read(STDIN_FILENO, buffer, BUFFER_LEN)) > 0) {
            if (write(pipe_to_child[1], buffer, nbyte) != nbyte) {
                // failed to write all of the input to program stdin
                break;
            }
        }

        // closing read end of pipe will signal EOF for the child process
        close(proc_pipe[1]);
        waitpid(child_pid, &status, 0);

        // tracer loop
        while (WIFSTOPPED(status)) {
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

        // disable queued timeout
        alarm(0);

        // record results for crash handler to analyse
        if (WIFSIGNALED(status) || (WIFSTOPPED(status) && WSTOPSIG(status) != SIGTRAP)) {
            int signal = WIFSIGNALED(status) ? WTERMSIG(status) : WSTOPSIG(status);
            fprintf(stdout, "crash_type:crash|signal:%d\n", signal);
        }
    }

    return 0;
}
