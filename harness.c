#include <stdio.h>
#include <stdlib.h>
#include <sys/ptrace.h>

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
    if (argc < 3) {
        fprintf(stderr, "Usage: %s <timeout_sec> <binary> <stdin>\n", argv[0]);
        return 1;
    }

    int timeout_seconds = atoi(argv[1]);
    char *binary_path = argv[2];
    char *input = argv[3];

    // create pipe to be able to redirect binary stdin
    int pipe[2];
    if (pipe(pipe) == -1) {
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
        close(pipe[1]);
        // redirect stdin to read from pipe
        dup2(pipe[0], STDIN_FILENO);
        close(pipe[0]);

        // allow parent to attach to process
        ptrace(PTRACE_TRACEME, 0, NULL, NULL);
        raise(SIGSTOP);

        // execute the binary with the input
        execv(target_path, NULL);
        perror("execv");
    } else {
        // parent process (will run the tracer)
        int status;
        struct user_regs_struct regs;

        // parent proc will only be writing
        close(pipe[0]);

        // set up a timeout
        signal(SIGALRM, alarm_handler);
        alarm(timeout_seconds);

        char buffer[BUFFER_LEN];
        ssize_t nbytes;
        // input into child procs stdin
        while ((nbytes = read(STDIN_FILENO, buffer, BUFFER_LEN)) > 0) {
            if (write(pipe_to_child[1], buffer, nbytes) != nbytes) {
                break;
            }
        }
        // closing read end of pipe will signal EOF for the child process
        close(pipe_to_child[1]);

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
