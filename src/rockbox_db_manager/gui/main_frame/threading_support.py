"""Threading support for background operations in the main frame.

This module provides the infrastructure for running database operations
in background threads while keeping the GUI responsive.
"""

import sys
import threading
import traceback
import functools
from typing import Callable, Optional, Any

from ..error_handling import show_error_dialog
from ..thread_events import ThreadEvent
import wx


class ThreadingSupport:
    """Handles threading operations for the main frame."""

    def __init__(self, frame):
        """Initialize threading support.
        
        Args:
            frame: The MyFrame instance
        """
        self.frame = frame

    def start_thread(self, func: Callable, *args: Any, **kwargs: Any) -> None:
        """Execute a func with *args and **kwargs in a new thread.

        Event handlers can be bound as kwargs using the keys:
            _start: Called when thread starts
            _message: Called for progress updates
            _end: Called when thread completes

        An Info object that will be passed to the event handlers can be
        specified with the kwarg '_info'

        Args:
            func: The function to execute in the thread
            *args: Positional arguments to pass to func
            **kwargs: Keyword arguments to pass to func (special keys prefixed with _ are intercepted)
        """
        # Extract the event handler functions from kwargs, and remove them,
        # so they aren't passed to func
        end_handler: Callable = kwargs.pop("_end", lambda evt: None)
        start_handler: Optional[Callable] = kwargs.pop("_start", None)
        msg_handler: Optional[Callable] = kwargs.pop("_message", None)
        info = kwargs.pop("_info", None)

        if info is not None:
            self.frame.thread_info.append(info)

        # Worker function that will be called in the thread
        def worker() -> None:
            try:
                # Post start event if handler provided
                if start_handler:
                    ThreadEvent.post_start(self.frame, start_handler, info)

                # Replace the callback with one that knows its handler
                if msg_handler:
                    thread_callback = functools.partial(
                        ThreadEvent.post_callback, self.frame, msg_handler, info
                    )
                    # Update all callback types in kwargs if present
                    if "callback" in kwargs:
                        kwargs["callback"] = thread_callback
                    if "dircallback" in kwargs:
                        kwargs["dircallback"] = thread_callback
                    if "filecallback" in kwargs:
                        kwargs["filecallback"] = thread_callback
                    if "estimatecallback" in kwargs:
                        kwargs["estimatecallback"] = thread_callback

                # Execute the actual function
                func(*args, **kwargs)

                # Post end event
                ThreadEvent.post_end(self.frame, end_handler, info)

            except SystemExit:
                # Allow clean thread termination
                pass
            except Exception as e:
                # Catch any unexpected errors
                error_details = traceback.format_exc()
                print(f"Thread error: {e}", file=sys.stderr)
                print(error_details, file=sys.stderr)
                # Show error dialog to user
                wx.CallAfter(
                    show_error_dialog, self.frame, "Thread Error", str(e), error_details
                )

        # Create and start the daemon thread
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
