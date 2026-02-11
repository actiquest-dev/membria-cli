"""Process management for Membria daemon."""

import os
import signal
import subprocess
import time
import logging
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ProcessStatus:
    """Status of a managed process."""
    is_running: bool
    pid: Optional[int] = None
    uptime_seconds: Optional[float] = None
    port: Optional[int] = None
    graph_connected: bool = False


class ProcessManager:
    """Manage daemon process lifecycle."""

    def __init__(self, config_dir: Path = None):
        """Initialize process manager."""
        if config_dir is None:
            config_dir = Path.home() / ".membria"
        self.config_dir = config_dir
        self.pid_file = config_dir / "daemon.pid"
        self.log_dir = config_dir / "logs"
        self.log_file = self.log_dir / "daemon.log"
        self.start_time_file = config_dir / "daemon.start_time"

        # Create directories
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def start(self, port: int = 3117, auto_start: bool = True) -> Tuple[bool, str]:
        """
        Start the daemon process.

        Returns:
            (success, message)
        """
        # Check if already running
        if self.is_running():
            pid = self._read_pid()
            return False, f"Daemon already running (PID: {pid})"

        # Check port availability
        if not self._is_port_available(port):
            return False, f"Port {port} is already in use"

        try:
            # Start daemon process
            from membria.daemon import MembriaDaemon

            daemon = MembriaDaemon()

            # Use subprocess to detach the daemon
            # Note: In production, we'd use proper daemonization
            # For now, we'll implement a simple version
            process = subprocess.Popen(
                ["python", "-m", "membria.daemon_main"],
                stdout=open(self.log_file, "a"),
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                preexec_fn=os.setsid if os.name != "nt" else None,
                cwd=str(Path(__file__).parent.parent.parent),
            )

            # Save PID
            self._write_pid(process.pid)
            self._write_start_time()

            # Give process time to start and verify it's running
            time.sleep(0.5)

            if not self._check_process_running(process.pid):
                return False, "Failed to start daemon (process exited)"

            logger.info(f"Daemon started (PID: {process.pid})")
            return True, f"Daemon started on port {port} (PID: {process.pid})"

        except Exception as e:
            logger.error(f"Failed to start daemon: {e}")
            return False, f"Failed to start daemon: {e}"

    def stop(self) -> Tuple[bool, str]:
        """
        Stop the daemon process.

        Returns:
            (success, message)
        """
        if not self.is_running():
            return False, "Daemon is not running"

        try:
            pid = self._read_pid()

            # Try graceful shutdown first
            if os.name != "nt":
                os.killpg(os.getpgid(pid), signal.SIGTERM)
            else:
                subprocess.run(["taskkill", "/PID", str(pid)], check=False)

            # Wait for process to terminate
            for _ in range(10):
                if not self._check_process_running(pid):
                    self.pid_file.unlink(missing_ok=True)
                    self.start_time_file.unlink(missing_ok=True)
                    logger.info(f"Daemon stopped (was PID: {pid})")
                    return True, f"Daemon stopped (was PID: {pid})"
                time.sleep(0.1)

            # Force kill if still running
            if os.name != "nt":
                os.killpg(os.getpgid(pid), signal.SIGKILL)
            else:
                subprocess.run(["taskkill", "/PID", str(pid), "/F"], check=False)

            self.pid_file.unlink(missing_ok=True)
            self.start_time_file.unlink(missing_ok=True)
            return True, f"Daemon force-stopped"

        except Exception as e:
            logger.error(f"Failed to stop daemon: {e}")
            return False, f"Failed to stop daemon: {e}"

    def status(self, port: int = 3117) -> ProcessStatus:
        """
        Get daemon status.

        Returns:
            ProcessStatus object
        """
        is_running = self.is_running()
        pid = self._read_pid() if is_running else None
        uptime = None

        if is_running and pid:
            uptime = self._get_uptime()

        return ProcessStatus(
            is_running=is_running,
            pid=pid,
            uptime_seconds=uptime,
            port=port,
            graph_connected=False  # TODO: Check actual connection
        )

    def get_logs(self, follow: bool = False, lines: int = 50) -> str:
        """
        Get daemon logs.

        Args:
            follow: If True, follow log output
            lines: Number of lines to show

        Returns:
            Log content as string
        """
        if not self.log_file.exists():
            return "No logs available"

        try:
            if follow:
                # In a real implementation, we'd use tail -f
                # For now, return current logs
                return self.log_file.read_text()
            else:
                # Get last N lines
                with open(self.log_file, "r") as f:
                    all_lines = f.readlines()
                    return "".join(all_lines[-lines:])
        except Exception as e:
            return f"Error reading logs: {e}"

    def is_running(self) -> bool:
        """Check if daemon is running."""
        if not self.pid_file.exists():
            return False

        try:
            pid = self._read_pid()
            return self._check_process_running(pid)
        except Exception:
            return False

    def _write_pid(self, pid: int) -> None:
        """Write PID to file."""
        self.pid_file.write_text(str(pid))

    def _read_pid(self) -> int:
        """Read PID from file."""
        return int(self.pid_file.read_text().strip())

    def _write_start_time(self) -> None:
        """Write start time to file."""
        self.start_time_file.write_text(str(time.time()))

    def _get_uptime(self) -> Optional[float]:
        """Get daemon uptime in seconds."""
        try:
            if self.start_time_file.exists():
                start_time = float(self.start_time_file.read_text().strip())
                return time.time() - start_time
        except Exception:
            pass
        return None

    def _check_process_running(self, pid: int) -> bool:
        """Check if process is running."""
        try:
            if os.name == "nt":
                # Windows
                result = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {pid}"],
                    capture_output=True,
                    text=True
                )
                return str(pid) in result.stdout
            else:
                # Unix
                os.kill(pid, 0)  # Check if process exists
                return True
        except (ProcessLookupError, OSError):
            return False

    def _is_port_available(self, port: int) -> bool:
        """Check if port is available."""
        try:
            import socket
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
                return True
        except OSError:
            return False
