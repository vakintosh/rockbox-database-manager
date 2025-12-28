"""GUI sub-package for Rockbox Database Manager.

This package provides a modular wxPython GUI implementation with clear
separation of concerns. The original large gui.py file has been refactored
into focused modules:

Modules:
    app.py: Application entry point and main app class
    main_frame/: Main window (further split into sub-modules)
        - frame.py: MyFrame class and initialization
        - format_manager.py: Format string management
        - database_operations.py: Database operation handlers
        - thread_handlers.py: Thread event handlers
        - threading_support.py: Thread coordination utilities
    field_panes.py: Database field browsing panels
    info_panel.py: Progress tracking UI components
    error_handling.py: Error dialogs and validation
    thread_events.py: Custom threading events for wxPython
"""

from .app import MyApp, main
from .main_frame import MyFrame
from .field_panes import FieldPane, FieldPanePanel
from .error_handling import show_error_dialog, show_warning_dialog, validate_path, validate_format_string
from .thread_events import ThreadEvent, EVT_THREAD_START, EVT_THREAD_CALLBACK, EVT_THREAD_END
from .info_panel import InfoPanel, Info
from .async_operations import AsyncIOSupport, AsyncDatabaseOperations, create_progress_callback
from .cancellable_progress import CancellableProgressDialog, NonModalProgressDialog

__all__ = [
    'MyApp',
    'main',
    'MyFrame',
    'FieldPane',
    'FieldPanePanel',
    'show_error_dialog',
    'show_warning_dialog',
    'validate_path',
    'validate_format_string',
    'ThreadEvent',
    'EVT_THREAD_START',
    'EVT_THREAD_CALLBACK',
    'EVT_THREAD_END',
    'InfoPanel',
    'Info',
    'AsyncIOSupport',
    'AsyncDatabaseOperations',
    'create_progress_callback',
    'CancellableProgressDialog',
    'NonModalProgressDialog',
]
