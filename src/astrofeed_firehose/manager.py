import time
import traceback
from faster_fifo import Queue
from multiprocessing import Process, Value
from multiprocessing.sharedctypes import Synchronized
from astrofeed_firehose.config import (
    QUEUE_BUFFER_SIZE,
    MANAGER_CHECK_INTERVAL,
    CPU_COUNT,
)


class FirehoseProcessingManager:
    def __init__(self):
        """An overall management class ran on the main thread. It owns & starts the
        queue and processes in the processing flow. It also has an additional monitor
        function that can be called to continuously monitor the individual subprocesses,
        looking for hung processes or other issues.
        """
        # Fixed resources
        self.cursor: Synchronized = Value("L", 0)
        self.op_count: Synchronized = Value("L", 0)

        # Multiprocessing primitives
        self.queue: Queue = Queue(QUEUE_BUFFER_SIZE)
        self.processes: list[Process] = []
        self.times: list[Synchronized] = []
        self._initialize_processes()

        # Values to help FirehoseProcessingManager.monitor() work
        self.last_check_time: float = time.time()
        self.last_op_count: int = 0

    def start_processes(self):
        """Starts all child processes."""
        for process in self.processes:
            process.start()

    def stop_processes(self):
        """Tries to kill child processes."""
        for process in self.processes:
            try:
                process.kill()
            except Exception as ex:
                print(f"Exception stopping worker {process.name} ({ex})")
                pass

    def monitor(self):
        """Monitors running processes and asserts that they are still running."""
        while True:
            self._print_ops_per_second()
            dead_processes, hung_processes = self._check_processes()
            if dead_processes or hung_processes:
                self.stop_processes()
                raise RuntimeError(
                    "Processes encountered critical errors and hung/died."
                    f"\nProcesses that died: {dead_processes}"
                    f"\nProcesses that hung: {hung_processes}"
                )
            time.sleep(MANAGER_CHECK_INTERVAL)

    def _initialize_processes(self):
        """Performs set up on all initial processes, creating a firehose_client process
        and CPU_COUNT commit processor processes.
        """
        name = "Firehose client"
        target = _run_firehose_client
        kwargs = dict()

        for i in range(CPU_COUNT + 1):
            # Create resources for one process
            self.times.append(Value("d", time.time()))
            self.processes.append(
                Process(
                    target=target,
                    args=(self.queue, self.cursor, self.times[-1]),
                    kwargs=kwargs,
                    name=name,
                )
            )

            # Set up a couple of things for the next loop
            name = f"Commit processor {i + 1}"
            target = _run_commit_processor
            kwargs = dict(op_counter=self.op_count)

    def _check_processes(self) -> tuple[list[str], list[str]]:
        """Checks all processes and works out which are hung or dead."""
        latest_possible_update = time.time() - MANAGER_CHECK_INTERVAL
        dead_processes = []
        hung_processes = []
        for process, process_last_update in zip(self.processes, self.times):
            # Check for outright dead processes
            if not process.is_alive():
                dead_processes.append(process.name)
                continue

            # Check for hung processes
            if process_last_update.value < latest_possible_update:
                hung_processes.append(process.name)

        return dead_processes, hung_processes

    def _print_ops_per_second(self):
        """Prints the total number of ops/second."""
        current_time, current_op_count = time.time(), self.op_count.value

        time_elapsed = current_time - self.last_check_time
        ops_elapsed = current_op_count - self.last_op_count
        print(
            f"Running at {ops_elapsed / time_elapsed:.2f} ops/sec "
            f"(total: {current_op_count} ops)"
        )

        self.last_check_time, self.last_op_count = current_time, current_op_count


def _run_firehose_client(
    queue: Queue,
    cursor: Synchronized,  # Return value of multiprocessing.Value
    firehose_time: Synchronized,  # Return value of multiprocessing.Value
    **kwargs,
):
    """Entry point for the firehose client subprocess.

    The main purpose of this function is to delay import of any database-related stuff
    until after we're running on a subprocess.
    """
    from astrofeed_firehose.firehose_client import run_client

    try:
        run_client(queue, cursor, firehose_time, **kwargs)
    except Exception as e:
        print(traceback.format_exc())
        raise e


def _run_commit_processor(
    queue: Queue,
    cursor: Synchronized,  # Return value of multiprocessing.Value
    firehose_time: Synchronized,  # Return value of multiprocessing.Value
    **kwargs,
):
    """Entry point for the commit processor subprocesses.

    The main purpose of this function is to delay import of any database-related stuff
    until after we're running on a subprocess.
    """
    from astrofeed_firehose.commit_processor import run_commit_processor

    try:
        run_commit_processor(queue, cursor, firehose_time, **kwargs)
    except Exception as e:
        print(traceback.format_exc())
        raise e
