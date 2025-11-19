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

/* Constants */
#define BUFFER_LEN 4096
#define MAX_OUTPUT_LEN 50000
#define MAX_COVERAGE_SIZE 65536
#define MAX_BREAKPOINTS 10000

/* Typedefs */
typedef struct {
    uintptr_t addr;
    uintptr_t offset;
    long data;
    bool active;
} breakpoint;

/* Globals */
uint8_t coverage_bitmap[MAX_COVERAGE_SIZE];
pid_t child_pid = -1;
breakpoint breakpoints[MAX_BREAKPOINTS];
int num_bps = 0;
char out_buf[MAX_OUTPUT_LEN] = {0};
char err_buf[MAX_OUTPUT_LEN] = {0};
int out_len = 0;
int err_len = 0;

void load_fn_symbols(char *binary_path) {
    char cmd[1024];
    // run nm to list symbols, grep for [T] (to find functions), then cut to only get the address
    snprintf(cmd, sizeof(cmd), "nm %s | grep ' T ' | cut -d' ' -f1", binary_path);

    FILE *fp = popen(cmd, "r");
    if (!fp) {
        perror("popen");
        return;
    }

    char line[20];
    while (fgets(line, sizeof(line), fp) && num_bps < MAX_BREAKPOINTS) {
        uintptr_t addr = strtoul(line, NULL, 16);
        if (addr != 0) {
            breakpoints[num_bps].offset = addr;
            breakpoints[num_bps].active = false;
            num_bps++;
        }
    }
    pclose(fp);
}

uintptr_t get_base_addr(pid_t pid) {
    char path[64];
    char line[256];
    snprintf(path, sizeof(path), "/proc/%d/maps", pid);

    FILE *fp = fopen(path, "r");
    if (!fp) {
        perror("fopen maps");
        return 0;
    }

    uintptr_t base_addr = 0;
    // first line of maps is the text segment base
    if (fgets(line, sizeof(line), fp)) {
        char *dash = strchr(line, '-');
        if (dash) {
            *dash = '\0';
            base_addr = strtoul(line, NULL, 16);
        }
    }
    fclose(fp);
    return base_addr;
}

void enable_breakpoint(pid_t pid, int idx) {
    if (idx < 0 || idx >= num_bps) {
        return;
    }

    uintptr_t addr = breakpoints[idx].addr;

    // get the word at the address
    long data = ptrace(PTRACE_PEEKTEXT, pid, addr, NULL);
    breakpoints[idx].data = data;

    // in order for the breakpoint to work and trap, we write 0xCC to the lowest byte
    // 0xCC is the opcode for the int3 instruction (i.e. generating a breakpoint exception)
    long data_with_trap = (data & ~0xFF) | 0xCC;

    ptrace(PTRACE_POKETEXT, pid, addr, data_with_trap);
    breakpoints[idx].active = true;
}

void disable_breakpoint(pid_t pid, int idx) {
    if (idx < 0 || idx >= num_bps || !breakpoints[idx].active) {
        return;
    }

    uintptr_t addr = breakpoints[idx].addr;
    // replace the overwritten instruction with the original one (i.e. one without the bp exception)
    ptrace(PTRACE_POKETEXT, pid, addr, breakpoints[idx].data);
    breakpoints[idx].active = false;
}

int find_breakpoint_index(uintptr_t addr) {
    for (int i = 0; i < num_bps; i++) {
        if (breakpoints[i].addr == addr) return i;
    }
    return -1;
}

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

void print_output(int out_fd, int err_fd) {
    char buffer[BUFFER_LEN];
    ssize_t n;

    while ((n = read(out_fd, buffer, sizeof(buffer))) > 0) {
        if (out_len + n < MAX_OUTPUT_LEN - 1) {
            memcpy(out_buf + out_len, buffer, n);
            out_len += n;
        }
    }

    while ((n = read(err_fd, buffer, sizeof(buffer))) > 0) {
        if (err_len + n < MAX_OUTPUT_LEN - 1) {
            memcpy(err_buf + err_len, buffer, n);
            err_len += n;
        }
    }
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <timeout_sec> <binary>\n", argv[0]);
        return 1;
    }

    int timeout_seconds = atoi(argv[1]);
    char *binary_path = argv[2];

    // detect all function/text segment symbols in the given binary
    load_fn_symbols(binary_path);

    // create pipe to be able to redirect binary stdin/stdout/stderr and harness stdin/stdout/stderr
    int stdin_pipe[2];      // parent writes, child reads
    int stdout_pipe[2];     // child writes, parent reads
    int stderr_pipe[2];     // child writes, parent reads
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
        // raise(SIGSTOP);

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

        // wait for execve to finish
        waitpid(child_pid, &status, 0);

        // if ASLR is enabled, we need to find the base address to be able to compare with
        // the nm output
        uintptr_t base_addr = get_base_addr(child_pid);
        if (base_addr == 0) {
            kill(child_pid, SIGKILL);
            return 1;
        }

        // set up actual address (i.e. offset + PIE base address)
        for (int i = 0; i < num_bps; i++) {
            breakpoints[i].addr = base_addr + breakpoints[i].offset;
            enable_breakpoint(child_pid, i);
        }

        // set up a timeout
        signal(SIGALRM, timeout_handler);
        alarm(timeout_seconds);

        // set pipes to nonblocking (so reads dont block ptrace loop)
        fcntl(stdout_pipe[0], F_SETFL, O_NONBLOCK);
        fcntl(stderr_pipe[0], F_SETFL, O_NONBLOCK);

        // input the stdin to the binary
        char buffer[BUFFER_LEN];
        ssize_t nbyte;
        while ((nbyte = read(STDIN_FILENO, buffer, BUFFER_LEN)) > 0) {
            write(stdin_pipe[1], buffer, nbyte);
        }
        // closing read end of pipe will signal EOF for the child process
        close(stdin_pipe[1]);

        // resume execution
        ptrace(PTRACE_CONT, child_pid, NULL, NULL);

        // tracer loop
        while (WIFSTOPPED(status)) {
            waitpid(child_pid, &status, 0);

            print_output(stdout_pipe[0], stderr_pipe[0]);

            if (WIFEXITED(status) || WIFSIGNALED(status)) {
                break;
            }

            if (WIFSTOPPED(status)) {
                int sig = WSTOPSIG(status);

                // if signal was a SIGTRAP, then we hit a breakpoint, record coverage
                if (sig == SIGTRAP) {
                    ptrace(PTRACE_GETREGS, child_pid, NULL, &regs);
                    uintptr_t trap_addr = regs.rip - 1;
                    int bp_idx = find_breakpoint_index(trap_addr);

                    if (bp_idx != -1) {
                        add_coverage(breakpoints[bp_idx].offset);

                        // restore original instruction
                        disable_breakpoint(child_pid, bp_idx);

                        // decrement rip by 1 so it repeats the now restored instruction
                        regs.rip = trap_addr;
                        ptrace(PTRACE_SETREGS, child_pid, NULL, &regs);
                    }

                    // resume execution
                    ptrace(PTRACE_CONT, child_pid, NULL, NULL);
                } else {
                    // signal was not a SIGTRAP the program stopped/crashed another way
                    ptrace(PTRACE_CONT, child_pid, 0, sig);
                }

            }
        }

        // write any last output that could've been flushed after process died
        print_output(stdout_pipe[0], stderr_pipe[0]);
        out_buf[out_len] = '\0';
        err_buf[err_len] = '\0';

        // disable queued timeout
        alarm(0);

        // write child proc's stdout to harness stdout
        if (out_len > 0) {
            fprintf(stdout, "STDOUT:");
            fwrite(out_buf, 1, out_len, stdout);
        }

        // write child proc's stderr to harness stdout
        if (err_len > 0) {
            fprintf(stdout, "|STDERR:");
            fwrite(err_buf, 1, err_len, stdout);
        }
        fflush(stdout);

        // record results for crash handler to analyse
        if (WIFSIGNALED(status)) {
            int sig = WTERMSIG(status);
            if (sig == SIGKILL) {
                fprintf(stderr, "CRASH_TYPE:timeout|SIGNAL:%d", sig);
            } else {
                fprintf(stderr, "CRASH_TYPE:crash|SIGNAL:%d", sig);
            }
        } else {
            fprintf(stderr, "CRASH_TYPE:none|SIGNAL:0");
        }

        // record the coverage results
        fprintf(stderr, "|COVERAGE:");
        bool first_cov = true;
        for (int i = 0; i < MAX_COVERAGE_SIZE; i++) {
            if (coverage_bitmap[i]) {
                if (!first_cov) {
                    fprintf(stderr, ",");
                }
                fprintf(stderr, "%x", i);
                first_cov = false;
            }
        }
        fprintf(stderr, "\n");

    }

    return 0;
}
