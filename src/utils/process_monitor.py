"""
Process monitor for the Startup Finder.

This module provides utilities for monitoring the Startup Finder process,
including performance tracking, bottleneck detection, and optimization suggestions.
"""

import time
import logging
import threading
import psutil
import os
from typing import Dict, Any, List, Optional, Callable, Tuple
from collections import deque

# Set up logging
logger = logging.getLogger(__name__)

class ProcessMonitor:
    """Monitor the Startup Finder process and provide optimization suggestions."""

    def __init__(self, update_interval: float = 1.0, history_size: int = 60):
        """
        Initialize the process monitor.

        Args:
            update_interval: Interval in seconds between updates
            history_size: Number of data points to keep in history
        """
        self.update_interval = update_interval
        self.history_size = history_size
        self.running = False
        self.monitor_thread = None

        # Performance metrics
        self.cpu_history = deque(maxlen=history_size)
        self.memory_history = deque(maxlen=history_size)
        self.disk_io_history = deque(maxlen=history_size)
        self.network_io_history = deque(maxlen=history_size)

        # Process metrics
        self.process = psutil.Process(os.getpid())
        self.start_time = time.time()

        # Phase tracking
        self.current_phase = "initialization"
        self.phase_start_times = {"initialization": self.start_time}
        self.phase_durations = {}

        # Bottleneck detection
        self.bottlenecks = []
        self.optimization_suggestions = []

        # Callback for real-time optimization
        self.optimization_callback = None

    def start(self, optimization_callback: Optional[Callable] = None):
        """
        Start monitoring the process.

        Args:
            optimization_callback: Optional callback function for real-time optimization
        """
        if self.running:
            return

        self.running = True
        self.optimization_callback = optimization_callback
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        logger.info("Process monitor started")

    def stop(self):
        """Stop monitoring the process."""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2.0)
        logger.info("Process monitor stopped")

    def set_phase(self, phase: str):
        """
        Set the current processing phase.

        Args:
            phase: Name of the current phase
        """
        if phase == self.current_phase:
            return

        # Record end time of previous phase
        now = time.time()
        if self.current_phase in self.phase_start_times:
            start_time = self.phase_start_times[self.current_phase]
            duration = now - start_time
            self.phase_durations[self.current_phase] = duration
            logger.info(f"Phase '{self.current_phase}' completed in {duration:.2f} seconds")

        # Set new phase
        self.current_phase = phase
        self.phase_start_times[phase] = now
        logger.info(f"Entering phase: {phase}")

    def _monitor_loop(self):
        """Main monitoring loop."""
        last_disk_io = psutil.disk_io_counters()
        last_network_io = psutil.net_io_counters()
        last_time = time.time()

        while self.running:
            try:
                # Sleep for update interval
                time.sleep(self.update_interval)

                # Get current time
                current_time = time.time()
                time_diff = current_time - last_time

                # Get CPU usage
                cpu_percent = self.process.cpu_percent()
                self.cpu_history.append((current_time, cpu_percent))

                # Get memory usage
                memory_info = self.process.memory_info()
                memory_percent = self.process.memory_percent()
                self.memory_history.append((current_time, memory_percent))

                # Get disk I/O
                current_disk_io = psutil.disk_io_counters()
                disk_read_speed = (current_disk_io.read_bytes - last_disk_io.read_bytes) / time_diff
                disk_write_speed = (current_disk_io.write_bytes - last_disk_io.write_bytes) / time_diff
                self.disk_io_history.append((current_time, (disk_read_speed, disk_write_speed)))
                last_disk_io = current_disk_io

                # Get network I/O
                current_network_io = psutil.net_io_counters()
                network_recv_speed = (current_network_io.bytes_recv - last_network_io.bytes_recv) / time_diff
                network_sent_speed = (current_network_io.bytes_sent - last_network_io.bytes_sent) / time_diff
                self.network_io_history.append((current_time, (network_recv_speed, network_sent_speed)))
                last_network_io = current_network_io

                # Update last time
                last_time = current_time

                # Detect bottlenecks
                self._detect_bottlenecks()

                # Log status periodically (every 10 seconds)
                if int(current_time) % 10 == 0:
                    self._log_status()

                # Call optimization callback if needed
                if self.optimization_callback and self.bottlenecks:
                    self.optimization_callback(self.bottlenecks, self.optimization_suggestions)

            except Exception as e:
                logger.error(f"Error in process monitor: {e}")

    def _detect_bottlenecks(self):
        """Detect bottlenecks in the process."""
        self.bottlenecks = []
        self.optimization_suggestions = []

        # Check CPU usage
        if len(self.cpu_history) > 5:
            recent_cpu = [cpu for _, cpu in list(self.cpu_history)[-5:]]
            avg_cpu = sum(recent_cpu) / len(recent_cpu)

            if avg_cpu > 90:
                self.bottlenecks.append(("CPU", avg_cpu))
                self.optimization_suggestions.append(
                    "High CPU usage detected. Consider reducing the number of parallel processes."
                )
            elif avg_cpu < 30 and self.current_phase != "initialization":
                self.bottlenecks.append(("CPU", avg_cpu))
                self.optimization_suggestions.append(
                    "Low CPU usage detected. Consider increasing the number of parallel processes."
                )

        # Check memory usage
        if len(self.memory_history) > 5:
            recent_memory = [mem for _, mem in list(self.memory_history)[-5:]]
            avg_memory = sum(recent_memory) / len(recent_memory)

            if avg_memory > 80:
                self.bottlenecks.append(("Memory", avg_memory))
                self.optimization_suggestions.append(
                    "High memory usage detected. Consider reducing batch sizes or enabling more aggressive garbage collection."
                )

        # Check disk I/O
        if len(self.disk_io_history) > 5:
            recent_disk_write = [write for _, (_, write) in list(self.disk_io_history)[-5:]]
            avg_disk_write = sum(recent_disk_write) / len(recent_disk_write)

            if avg_disk_write > 10 * 1024 * 1024:  # 10 MB/s
                self.bottlenecks.append(("Disk I/O", avg_disk_write))
                self.optimization_suggestions.append(
                    "High disk write activity detected. Consider reducing logging verbosity or caching to memory."
                )

        # Check network I/O
        if len(self.network_io_history) > 5:
            recent_network_recv = [recv for _, (recv, _) in list(self.network_io_history)[-5:]]
            avg_network_recv = sum(recent_network_recv) / len(recent_network_recv)

            if avg_network_recv > 5 * 1024 * 1024:  # 5 MB/s
                self.bottlenecks.append(("Network I/O", avg_network_recv))
                self.optimization_suggestions.append(
                    "High network activity detected. Consider enabling more aggressive caching or reducing parallel requests."
                )
            elif avg_network_recv < 50 * 1024 and self.current_phase in ["crawling", "enrichment"]:  # 50 KB/s
                self.bottlenecks.append(("Network I/O", avg_network_recv))
                self.optimization_suggestions.append(
                    "Low network activity detected. Consider increasing the number of parallel requests."
                )

    def _log_status(self):
        """Log the current status of the process."""
        if not self.cpu_history or not self.memory_history:
            return

        # Get latest metrics
        _, cpu_percent = self.cpu_history[-1]
        _, memory_percent = self.memory_history[-1]

        # Calculate elapsed time
        elapsed_time = time.time() - self.start_time

        # Log status
        logger.info(
            f"Status: Phase={self.current_phase}, "
            f"CPU={cpu_percent:.1f}%, Memory={memory_percent:.1f}%, "
            f"Elapsed={elapsed_time:.1f}s"
        )

        # Log bottlenecks if any
        if self.bottlenecks:
            bottleneck_str = ", ".join(f"{name}={value:.1f}" for name, value in self.bottlenecks)
            logger.warning(f"Bottlenecks detected: {bottleneck_str}")

            for suggestion in self.optimization_suggestions:
                logger.warning(f"Suggestion: {suggestion}")

    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the process monitoring.

        Returns:
            Dictionary with monitoring summary
        """
        elapsed_time = time.time() - self.start_time

        # Calculate average metrics
        avg_cpu = sum(cpu for _, cpu in self.cpu_history) / len(self.cpu_history) if self.cpu_history else 0
        avg_memory = sum(mem for _, mem in self.memory_history) / len(self.memory_history) if self.memory_history else 0

        # Create summary
        summary = {
            "elapsed_time": elapsed_time,
            "current_phase": self.current_phase,
            "phase_durations": self.phase_durations.copy(),
            "avg_cpu_percent": avg_cpu,
            "avg_memory_percent": avg_memory,
            "bottlenecks": self.bottlenecks.copy(),
            "optimization_suggestions": self.optimization_suggestions.copy()
        }

        return summary

# Create a global process monitor instance
process_monitor = ProcessMonitor()

def real_time_optimization_callback(bottlenecks: List[Tuple[str, float]], suggestions: List[str]):
    """
    Callback function for real-time optimization.

    Args:
        bottlenecks: List of detected bottlenecks
        suggestions: List of optimization suggestions
    """
    # Implement real-time optimizations based on bottlenecks
    for bottleneck, value in bottlenecks:
        if bottleneck == "CPU" and value > 90:
            # Reduce parallel processes
            from src.utils.optimization_utils import ParallelProcessor
            ParallelProcessor.get_optimal_workers = lambda: max(2, os.cpu_count() // 2)
            logger.warning("Reducing parallel workers due to high CPU usage")

        elif bottleneck == "Memory" and value > 80:
            # Enable more aggressive garbage collection
            import gc
            gc.collect()
            logger.warning("Triggered garbage collection due to high memory usage")

        elif bottleneck == "Network I/O" and value < 50 * 1024:
            # Increase parallel requests
            from src.utils.optimization_utils import ParallelProcessor
            ParallelProcessor.get_optimal_workers = lambda: min(32, os.cpu_count() * 8)
            logger.warning("Increasing parallel workers due to low network activity")

# Start the process monitor with real-time optimization
def start_monitoring():
    """Start the process monitor with real-time optimization."""
    process_monitor.start(optimization_callback=real_time_optimization_callback)
    return process_monitor
