import wx
import wx.lib.newevent
import functools
import threading
import sys
import os
import traceback
from typing import Callable, Optional, Any

from .database import Database
from .defs import FORMATTED_TAGS
from . import wxFB_gui
from .config import Config


#-------------------------------------------------------------------------------
# Error Handling Utilities
#-------------------------------------------------------------------------------
def show_error_dialog(parent: Optional[wx.Window], title: str, message: str, 
                      details: Optional[str] = None) -> None:
    """Show a user-friendly error dialog.
    
    Args:
        parent: Parent window (can be None)
        title: Dialog title
        message: Main error message
        details: Optional detailed error information (e.g., stack trace)
    """
    if details:
        full_message = f"{message}\n\nDetails:\n{details}"
    else:
        full_message = message
    
    dlg = wx.MessageDialog(parent, full_message, title, 
                          wx.OK | wx.ICON_ERROR)
    dlg.ShowModal()
    dlg.Destroy()


def show_warning_dialog(parent: Optional[wx.Window], title: str, message: str) -> None:
    """Show a warning dialog.
    
    Args:
        parent: Parent window (can be None)
        title: Dialog title
        message: Warning message
    """
    dlg = wx.MessageDialog(parent, message, title, 
                          wx.OK | wx.ICON_WARNING)
    dlg.ShowModal()
    dlg.Destroy()


def validate_path(path: str, must_exist: bool = True) -> tuple[bool, str]:
    """Validate a file or directory path.
    
    Args:
        path: Path to validate
        must_exist: Whether the path must already exist
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not path or not path.strip():
        return False, "Path cannot be empty"
    
    path = path.strip()
    
    if must_exist and not os.path.exists(path):
        return False, f"Path does not exist: {path}"
    
    # Check if parent directory exists for output paths
    if not must_exist:
        parent = os.path.dirname(path)
        if parent and not os.path.exists(parent):
            return False, f"Parent directory does not exist: {parent}"
    
    return True, ""


def validate_format_string(format_str: str) -> tuple[bool, str]:
    """Validate a titleformat string.
    
    Args:
        format_str: Format string to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not format_str or not format_str.strip():
        return False, "Format string cannot be empty"
    
    # Basic validation - check for balanced brackets
    stack = []
    for i, char in enumerate(format_str):
        if char in '[(':
            stack.append((char, i))
        elif char in '])':
            if not stack:
                return False, f"Unmatched closing bracket at position {i}"
            opening, _ = stack.pop()
            if (char == ']' and opening != '[') or (char == ')' and opening != '('):
                return False, f"Mismatched brackets at position {i}"
    
    if stack:
        char, pos = stack[0]
        return False, f"Unclosed bracket '{char}' at position {pos}"
    
    return True, ""


#-------------------------------------------------------------------------------
# Thread events
#-------------------------------------------------------------------------------
# wxPython Phoenix: Use wx.lib.newevent instead of deprecated wx.NewEventType/PyEventBinder
ThreadStartEvent, EVT_THREAD_START = wx.lib.newevent.NewEvent()
ThreadCallbackEvent, EVT_THREAD_CALLBACK = wx.lib.newevent.NewEvent()
ThreadEndEvent, EVT_THREAD_END = wx.lib.newevent.NewEvent()

class ThreadEvent:
    """Helper class for posting thread events."""
    
    @staticmethod
    def post_start(obj, handler, info):
        evt = ThreadStartEvent(info=info, _handler=handler)
        wx.PostEvent(obj, evt)  # Post directly to frame
        wx.WakeUpIdle()

    @staticmethod
    def post_end(obj, handler, info):
        evt = ThreadEndEvent(info=info, _handler=handler)
        wx.PostEvent(obj, evt)  # Post directly to frame
        wx.WakeUpIdle()

    @staticmethod
    def post_callback(obj, handler, info, message, *args, **kwargs):
        evt = ThreadCallbackEvent(message=message, info=info, _handler=handler, args=args, **kwargs)
        wx.PostEvent(obj, evt)  # Post directly to frame
        wx.WakeUpIdle()


#-------------------------------------------------------------------------------
# Operation Information
#-------------------------------------------------------------------------------
class InfoPanel(wx.ScrolledWindow):
    def __init__(self, parent):
        wx.ScrolledWindow.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_SUNKEN)
        self.SetScrollRate(10,10)
        self.sizer = wx.FlexGridSizer(0, 4, 0, 0)
        self.sizer.AddGrowableCol(3)
        self.SetSizer(self.sizer)

    def MakeRow(self, description=''):
        """Create an Info object, add it to the sizer, and return it."""
        info = Info(self, description)
        self.sizer.Add(info.time_ctrl, 1, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        self.sizer.Add(info.description_ctrl, 1, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        self.sizer.Add(info.gauge_ctrl, 1, wx.ALL, 5)
        self.sizer.Add(info.status_ctrl, 1, wx.ALIGN_CENTER_VERTICAL | wx.ALL | wx.EXPAND, 5)
        self.sizer.Layout()
        self.Refresh()
        return info

class RapidlyUpdatingText(wx.Window):

    """A very simple static text control.
    
    wxStaticText tries to resize itself every time it is updated, which slows
    down the gui.

    """

    def __init__(self, parent, id, text='', pos=(-1, -1), size=(-1,-1), style=0):
        wx.Window.__init__(self, parent, id, pos, size, style)
        self.SetValue(text)
        self.Bind(wx.EVT_PAINT, self.OnPaint)

    def SetValue(self, text):
        self.text = text
        self.SetMinSize(self.GetTextExtent(text))
        self.Refresh()
        self.Update()
        # Also refresh parent to ensure changes are visible
        parent = self.GetParent()
        if parent:
            parent.Refresh()
            parent.Update()

    def GetValue(self):
        return self.text

    def OnPaint(self, evt):
        dc = wx.PaintDC(self)
        dc.SetFont(self.GetFont())
        dc.DrawText(self.text, 0,0)

class Info(object):
    def __init__(self, parent, description=''):
        self.parent = parent
        self.gauge_ctrl = wx.Gauge(parent, wx.ID_ANY, size = (-1, 15))
        self.gauge_ctrl.SetMinSize((150,15))
        self.time_ctrl = RapidlyUpdatingText(parent, wx.ID_ANY, '00:00')
        self.description_ctrl = RapidlyUpdatingText(parent, wx.ID_ANY, description)
        self.status_ctrl = RapidlyUpdatingText(parent, wx.ID_ANY, '')

        self.elapsed_time = 0

        class MyTimer(wx.Timer):
            def Notify(dummy_self):
                self.elapsed_time += 1
                # Format the time
                minutes, seconds = divmod(self.elapsed_time, 60)
                hours, minutes = divmod(minutes, 60)
                s = ''
                if hours:
                    s = '%d:' % hours
                s += '%02d:%02d' % (minutes, seconds)
                self.time_value = s  # Use time_value property, not time

        self.timer = MyTimer()
        self.timer.Start(1000)
        self.timer.Stop()

    def SetRange(self, range):
        self.gauge_ctrl.SetRange(range)

    # Allow access to the controls as properties
    def _make_property(name):
        name += '_ctrl'
        def __get(self):
            return getattr(self, name).GetValue()
        def __set(self, value):
            getattr(self, name).SetValue(value)
        return property(__get, __set)

    gauge = _make_property('gauge')
    time_value = _make_property('time')  # Renamed to avoid shadowing time module
    description = _make_property('description')
    status = _make_property('status')


#-------------------------------------------------------------------------------
# The frame
#-------------------------------------------------------------------------------
class MyFrame(wxFB_gui.Frame):
    def __init__(self, parent):
        wxFB_gui.Frame.__init__(self, parent)
        self.Bind(EVT_THREAD_START, self._on_thread_start)
        self.Bind(EVT_THREAD_CALLBACK, self._on_thread_message)
        self.Bind(EVT_THREAD_END, self._on_thread_end)
        
        # Initialize configuration
        self.config = Config()
        
        self.panes = FieldPanePanel(self.notebook)
        self.notebook.AddPage(self.panes, 'View')
        self.status.SetStatusWidths([200,-1])

        # Insert the info panel into the sizer
        self.infopanel = InfoPanel(self.mainpanel)
        self.mainpanel.GetSizer().Insert(0, self.infopanel, 1, wx.ALL | wx.EXPAND, 5)
        self.mainpanel.Layout()

        self.database = Database()

        self.thread_info = [] # List of currently running info panels

        # Restore window size and position from config
        width, height = self.config.get_window_size()
        x, y = self.config.get_window_position()
        self.SetSize(width, height)
        if x != -1 and y != -1:
            self.SetPosition((x, y))
        
        # Load saved format strings
        self._load_format_strings()
        
        # Add tooltips to format string controls
        self._add_format_tooltips()
        
        # Add right-click menu for templates
        self._add_template_menus()
        
        self.Show()

        self.Bind(wx.EVT_CLOSE, self.OnClose)
    
    def _on_thread_start(self, evt):
        if hasattr(evt, '_handler'):
            # Extract data from event to avoid using deleted event object
            handler = evt._handler
            info = evt.info if hasattr(evt, 'info') else None
            
            class EventData:
                pass
            event_data = EventData()
            event_data.info = info
            
            handler(event_data)
        wx.WakeUpIdle()

    def _on_thread_message(self, evt):
        if hasattr(evt, '_handler'):
            # Extract data from event to avoid using deleted event object
            handler = evt._handler
            info = evt.info if hasattr(evt, 'info') else None
            message = evt.message if hasattr(evt, 'message') else None
            
            class EventData:
                pass
            event_data = EventData()
            event_data.info = info
            event_data.message = message
            
            handler(event_data)
        wx.WakeUpIdle()

    def _on_thread_end(self, evt):
        if hasattr(evt, '_handler'):
            # Extract data from event before CallAfter, as event object gets deleted
            handler = evt._handler
            info = evt.info if hasattr(evt, 'info') else None
            
            # Create a simple container for the info
            class EventData:
                pass
            event_data = EventData()
            event_data.info = info
            
            # Wrap the handler in CallAfter to ensure the UI thread 
            # is definitely ready to process the layout change.
            wx.CallAfter(handler, event_data)
        
        if hasattr(evt, 'info') and evt.info in self.thread_info:
            self.thread_info.remove(evt.info)
        
        wx.WakeUpIdle()

    def _load_format_strings(self) -> None:
        """Load saved format strings into the GUI."""
        for field in FORMATTED_TAGS:
            # Get the control name (e.g., "artist" from "artist")
            control_name = field.replace(' ', '')
            
            # Get the controls
            format_ctrl = getattr(self, control_name, None)
            sort_ctrl = getattr(self, control_name + '_sort', None)
            
            if format_ctrl:
                # Get saved format string, or use current value if not saved
                saved_format = self.config.get_format(field)
                if saved_format is not None:
                    format_ctrl.SetValue(saved_format)
            
            if sort_ctrl:
                # Get saved sort format, or use current value if not saved
                saved_sort = self.config.get_sort_format(field)
                if saved_sort is not None:
                    sort_ctrl.SetValue(saved_sort)
    
    def _save_format_strings(self) -> None:
        """Save current format strings to config."""
        for field in FORMATTED_TAGS:
            # Get the control name
            control_name = field.replace(' ', '')
            
            # Get the controls
            format_ctrl = getattr(self, control_name, None)
            sort_ctrl = getattr(self, control_name + '_sort', None)
            
            if format_ctrl:
                # Save the format string
                format_str = format_ctrl.GetValue()
                self.config.set_format(field, format_str)
            
            if sort_ctrl:
                # Save the sort format
                sort_str = sort_ctrl.GetValue()
                self.config.set_sort_format(field, sort_str)
    
    def _add_format_tooltips(self) -> None:
        """Add helpful tooltips to format string controls."""
        
        # Common tooltip text explaining format syntax
        format_help = (
            "Titleformat Syntax:\n"
            "  %field% - Insert tag value (e.g., %artist%, %album%)\n"
            "  [text] - Optional text (shown only if all tags inside exist)\n"
            "  $function(args) - Function call\n\n"
            "Common Functions:\n"
            "  $swapprefix(text) - Move 'The/A/An' to end\n"
            "  $upper(text) - Convert to uppercase\n"
            "  $lower(text) - Convert to lowercase\n"
            "  $caps(text) - Capitalize first letter\n"
            "  $replace(text,old,new) - Replace text\n\n"
            "Examples:\n"
            "  %artist% → 'The Beatles'\n"
            "  $swapprefix(%artist%) → 'Beatles, The'\n"
            "  [(%date%) ]%album% → '(1967) Sgt Pepper' or 'Album Name'\n"
            "  %album artist% → Album artist tag value"
        )
        
        sort_help = (
            "Sort Format:\n"
            "Defines how this field is sorted in lists.\n"
            "Usually same as display format, but often uses\n"
            "$swapprefix() to ignore 'The', 'A', 'An' prefixes.\n\n"
            "Example: $swapprefix(%artist%)\n"
            "  'The Beatles' sorts as 'Beatles, The'"
        )
        
        # Add tooltips to all format controls
        for field in FORMATTED_TAGS:
            control_name = field.replace(' ', '')
            
            format_ctrl = getattr(self, control_name, None)
            if format_ctrl:
                format_ctrl.SetToolTip(format_help)
            
            sort_ctrl = getattr(self, control_name + '_sort', None)
            if sort_ctrl:
                sort_ctrl.SetToolTip(sort_help)
    
    def get_format_templates(self) -> dict:
        """Return a dictionary of common format string templates."""
        return {
            'Simple': {
                'artist': '%artist%',
                'album': '%album%',
                'genre': '%genre%',
                'composer': '%composer%',
                'comment': '%comment%',
                'albumartist': '%album artist%',
                'grouping': '%grouping%',
            },
            'With Sorting': {
                'artist': '%artist%',
                'artist_sort': '$swapprefix(%artist%)',
                'album': '%album%',
                'album_sort': '%album%',
                'genre': '%genre%',
                'genre_sort': '%genre%',
            },
            'Year + Album': {
                'album': '[(%date%) ]%album%',
                'album_sort': '[(%date%) ]%album%',
            },
            'Classical': {
                'artist': '%composer%',
                'artist_sort': '$swapprefix(%composer%)',
                'album': '%album%',
                'grouping': '%composer% - %title%',
            },
            'Compilation Friendly': {
                'artist': '$if(%album artist%,%album artist%,%artist%)',
                'artist_sort': '$if(%album artist%,$swapprefix(%album artist%),$swapprefix(%artist%))',
                'albumartist': '%album artist%',
                'albumartist_sort': '$swapprefix(%album artist%)',
            },
        }
    
    def _add_template_menus(self) -> None:
        """Add right-click context menus with templates to format controls."""
        
        # Get all format controls
        format_controls = []
        for field in FORMATTED_TAGS:
            control_name = field.replace(' ', '')
            format_ctrl = getattr(self, control_name, None)
            sort_ctrl = getattr(self, control_name + '_sort', None)
            
            if format_ctrl:
                format_controls.append((format_ctrl, field, False))
            if sort_ctrl:
                format_controls.append((sort_ctrl, field, True))
        
        # Bind right-click event to show template menu
        for ctrl, field, is_sort in format_controls:
            ctrl.Bind(wx.EVT_CONTEXT_MENU, 
                     lambda evt, c=ctrl, f=field, s=is_sort: self._show_template_menu(evt, c, f, s))
    
    def _show_template_menu(self, evt, ctrl, field, is_sort):
        """Show context menu with format templates."""
        menu = wx.Menu()
        
        # Add "Copy" and "Paste" options
        copy_item = menu.Append(wx.ID_ANY, "Copy")
        paste_item = menu.Append(wx.ID_ANY, "Paste")
        menu.AppendSeparator()
        
        # Bind copy/paste
        self.Bind(wx.EVT_MENU, lambda e: self._copy_format(ctrl), copy_item)
        self.Bind(wx.EVT_MENU, lambda e: self._paste_format(ctrl), paste_item)
        
        # Add template submenu
        template_menu = wx.Menu()
        templates = self.get_format_templates()
        
        for template_name, template_formats in templates.items():
            # Check if this template has a value for this field
            control_name = field.replace(' ', '')
            key = control_name + '_sort' if is_sort else control_name
            
            if key in template_formats:
                item = template_menu.Append(wx.ID_ANY, template_name)
                template_value = template_formats[key]
                self.Bind(wx.EVT_MENU, 
                         lambda e, v=template_value, c=ctrl: self._apply_template(c, v), 
                         item)
        
        if template_menu.GetMenuItemCount() > 0:
            menu.AppendSubMenu(template_menu, "Apply Template")
        
        # Show the menu
        self.PopupMenu(menu)
        menu.Destroy()
    
    def _copy_format(self, ctrl):
        """Copy format string to clipboard."""
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(ctrl.GetValue()))
            wx.TheClipboard.Close()
    
    def _paste_format(self, ctrl):
        """Paste format string from clipboard."""
        if wx.TheClipboard.Open():
            data = wx.TextDataObject()
            if wx.TheClipboard.GetData(data):
                ctrl.SetValue(data.GetText())
            wx.TheClipboard.Close()
    
    def _apply_template(self, ctrl, template_value):
        """Apply a template value to a control."""
        ctrl.SetValue(template_value)


    def OnLoadTags(self, evt):
        default_dir = self.config.get_last_tags_file()
        if default_dir:
            default_dir = os.path.dirname(default_dir)
        
        filename = wx.FileSelector('Load Tags', 
                                  default_path=default_dir or '',
                                  default_extension='.pkl')
        if not filename:
            return
        
        # Validate file path
        is_valid, error_msg = validate_path(filename, must_exist=True)
        if not is_valid:
            show_error_dialog(self, "Invalid File Path", error_msg)
            return
        
        # Save to config
        self.config.set_last_tags_file(filename)
        self.config.save()

        def OnStart(evt):
            evt.info.timer.Start()
        def OnMessage(evt):
            if isinstance(evt.message, int):
                evt.info.SetRange(evt.message)
                evt.info.gauge = 0
            else:
                evt.info.gauge += 1
                evt.info.status =evt.message
        def OnEnd(evt):
            evt.info.timer.Stop()
            evt.info.status = 'Done'
            # Force the InfoPanel to re-layout and repaint immediately
            evt.info.parent.Layout()
            evt.info.parent.Refresh()

        self.start_thread(
            self.database.load_tags,
                filename,
                callback = None,
            _start=OnStart, _message=OnMessage, _end=OnEnd,
            _info=self.infopanel.MakeRow('Loading saved tags')
        )

    def OnSaveTags(self, evt):
        filename = wx.FileSelector('Save Tags', default_extension='.pkl')
        if not filename:
            return

        def OnStart(evt):
            evt.info.timer.Start()
        def OnMessage(evt):
            if isinstance(evt.message, int):
                evt.info.SetRange(evt.message)
                evt.info.gauge = 0
            else:
                evt.info.gauge += 1
                evt.info.status =evt.message
        def OnEnd(evt):
            evt.info.timer.Stop()
            evt.info.status = 'Done'
            # Force the InfoPanel to re-layout and repaint immediately
            evt.info.parent.Layout()
            evt.info.parent.Refresh()

        self.start_thread(
            self.database.save_tags,
                filename,
                callback = None,
            _start=OnStart, _message=OnMessage, _end=OnEnd,
            _info = self.infopanel.MakeRow('Saving tags')
        )

    def OnAddDirectory(self, evt):
        default_dir = self.config.get_last_music_dir()
        dir = wx.DirSelector('Music Directory',
                            default_path=default_dir or '')
        if not dir:
            return
        
        # Validate directory path
        is_valid, error_msg = validate_path(dir, must_exist=True)
        if not is_valid:
            show_error_dialog(self, "Invalid Directory Path", error_msg)
            return
        
        # Save to config
        self.config.set_last_music_dir(dir)
        self.config.save()

        def OnStart(evt):
            evt.info.timer.Start()
        def OnMessage(evt):
            if isinstance(evt.message, int):
                evt.info.SetRange(evt.message)
            else:
                evt.info.status = evt.message
                evt.info.gauge += 1
        def OnEnd(evt):
            evt.info.timer.Stop()
            evt.info.status = 'Done'
            # Force the InfoPanel to re-layout and repaint immediately
            evt.info.parent.Layout()
            evt.info.parent.Refresh()

        self.start_thread(
            self.database.add_dir,
                dir,
                dircallback = None,
                filecallback = None,
                estimatecallback = None,
            _start=OnStart, _message=OnMessage, _end=OnEnd,
            _info = self.infopanel.MakeRow('Adding %s' % dir)
        )

    def OnGenerateDatabase(self, evt):
        # Collect format strings from GUI (fast operation)
        format_strings = {}
        for field in FORMATTED_TAGS:
            format_str = self.__dict__[field.replace(' ','')].GetValue()
            sort_str = self.__dict__[field.replace(' ','')+'_sort'].GetValue()
            format_strings[field] = (format_str, sort_str)

        # Create info panel and show immediate status
        info = self.infopanel.MakeRow('Generating database')
        info.status = 'Starting...'
        info.timer.Start()
        
        # Force GUI to update immediately
        wx.Yield()

        def OnStart(evt):
            evt.info.status = 'Compiling format strings...'
        def OnMessage(evt):
            if isinstance(evt.message, str) and evt.message.startswith('READY:'):
                # Format strings compiled, now set the range for file processing
                count = int(evt.message.split(':')[1])
                evt.info.SetRange(count)
                evt.info.gauge = 0
                evt.info.status = 'Processing files...'
            else:
                evt.info.status = evt.message
                evt.info.gauge += 1
        def OnEnd(evt):
            evt.info.timer.Stop()
            evt.info.status = 'Done'
            # Force the InfoPanel to re-layout and repaint immediately
            evt.info.parent.Layout()
            evt.info.parent.Refresh()
            DatabaseEvent.post_updated(self.panes, self.database)

        def worker_generate_database(format_strings, callback=None):
            # Compile format strings in worker thread (may be slow)
            for field, (format_str, sort_str) in format_strings.items():
                self.database.set_format(field, format_str, sort_str)
            
            # Signal that we're ready to process files
            if callback:
                callback(f'READY:{len(self.database.paths)}')
            
            # Now generate the database
            self.database.generate_database(callback=callback)

        self.start_thread(
            worker_generate_database,
                format_strings,
                callback = None,
            _start=OnStart, _message=OnMessage, _end=OnEnd,
            _info = info
        )

    def OnWriteDatabase(self, evt):
        default_dir = self.config.get_last_output_dir()
        write_dir = wx.DirSelector('Database Output Directory',
                                  default_path=default_dir or '')
        if not write_dir:
            return
        
        # Validate directory path
        is_valid, error_msg = validate_path(write_dir, must_exist=False)
        if not is_valid:
            show_error_dialog(self, "Invalid Directory Path", error_msg)
            return
        
        # Create directory if it doesn't exist
        try:
            os.makedirs(write_dir, exist_ok=True)
        except OSError as e:
            show_error_dialog(self, "Directory Creation Failed", 
                            f"Could not create directory: {e}")
            return
        
        # Save to config
        self.config.set_last_output_dir(write_dir)
        self.config.save()

        def OnStart(evt):
            evt.info.timer.Start()
            evt.info.SetRange(9)
        def OnMessage(evt):
            if evt.message == 'done':
                evt.info.gauge += 1
            else:
                evt.info.status = evt.message
        def OnEnd(evt):
            evt.info.timer.Stop()
            evt.info.status = 'Done'
            # Force the InfoPanel to re-layout and repaint immediately
            evt.info.parent.Layout()
            evt.info.parent.Refresh()
            DatabaseEvent.post_updated(self.panes, self.database)

        self.start_thread(
            self.database.write,
                write_dir,
                callback = None,
            _start=OnStart, _message=OnMessage, _end=OnEnd,
            _info = self.infopanel.MakeRow('Writing database')
        )

    def OnReadDatabase(self, evt):
        default_dir = self.config.get_last_output_dir()
        read_dir = wx.DirSelector('Database Directory',
                                 default_path=default_dir or '')
        if not read_dir:
            return
        
        # Validate directory path
        is_valid, error_msg = validate_path(read_dir, must_exist=True)
        if not is_valid:
            show_error_dialog(self, "Invalid Directory Path", error_msg)
            return
        
        # Save to config
        self.config.set_last_output_dir(read_dir)
        self.config.save()

        def OnStart(evt):
            evt.info.timer.Start()
            evt.info.SetRange(9)
        def OnMessage(evt):
            if evt.message == 'done':
                evt.info.gauge += 1
            else:
                evt.info.status = evt.message
        def OnEnd(evt):
            evt.info.timer.Stop()
            evt.info.status = 'Done'
            # Force the InfoPanel to re-layout and repaint immediately
            evt.info.parent.Layout()
            evt.info.parent.Refresh()
            DatabaseEvent.post_updated(self.panes, self.database)

        def read_database(directory, callback=None):
            self.database = Database.read(directory, callback)

        self.start_thread(
            read_database,
                read_dir,
                callback = None,
            _start=OnStart, _message=OnMessage, _end=OnEnd,
            _info = self.infopanel.MakeRow('Reading database')
        )

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
        end_handler: Callable = kwargs.pop('_end', lambda evt: None)
        start_handler: Optional[Callable] = kwargs.pop('_start', None)
        msg_handler: Optional[Callable] = kwargs.pop('_message', None)
        info = kwargs.pop('_info', None)
        
        if info is not None:
            self.thread_info.append(info)

        # Worker function that will be called in the thread
        def worker() -> None:
            try:
                # Post start event if handler provided
                if start_handler:
                    ThreadEvent.post_start(self, start_handler, info)

                # Replace the callback with one that knows its handler
                if msg_handler:
                    thread_callback = functools.partial(
                        ThreadEvent.post_callback, self, msg_handler, info
                    )
                    # Update all callback types in kwargs if present
                    if 'callback' in kwargs:
                        kwargs['callback'] = thread_callback
                    if 'dircallback' in kwargs:
                        kwargs['dircallback'] = thread_callback
                    if 'filecallback' in kwargs:
                        kwargs['filecallback'] = thread_callback
                    if 'estimatecallback' in kwargs:
                        kwargs['estimatecallback'] = thread_callback

                # Execute the actual function
                func(*args, **kwargs)

                # Post end event
                ThreadEvent.post_end(self, end_handler, info)

            except SystemExit:
                # Allow clean thread termination
                pass
            except Exception as e:
                # Catch any unexpected errors
                error_details = traceback.format_exc()
                print(f"Thread error: {e}", file=sys.stderr)
                print(error_details, file=sys.stderr)
                # Show error dialog to user
                wx.CallAfter(show_error_dialog, self, 
                           "Thread Error",
                           str(e),
                           error_details)

        # Create and start the daemon thread
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()



    def OnClose(self, evt):
        # Save window size and position
        if not self.IsMaximized() and not self.IsIconized():
            size = self.GetSize()
            pos = self.GetPosition()
            self.config.set_window_size(size.width, size.height)
            self.config.set_window_position(pos.x, pos.y)
        
        # Save format strings
        self._save_format_strings()
        
        # Save configuration
        self.config.save()
        
        # Stop all running threads
        for info in self.thread_info:
            info.timer.Stop()
        
        evt.Skip()

#-------------------------------------------------------------------------------
# Field Pane
#-------------------------------------------------------------------------------
class FieldPane(wxFB_gui.FieldPane):
    def __init__(self, parent):
        wxFB_gui.FieldPane.__init__(self, parent)
        self.entries = []
        self.field = self.choice.GetStringSelection().lower()

    def UpdateListBox(self):
        if self.field == '<none>':
            self.listbox.Set( ['<All>'] )
            self.PostEvent('<All>')
            return

        values = {}
        for entry in self.entries:
            value = entry[self.field]
            if value not in values:
                values[value.data] = value.sort_value()

        values = sorted(values.keys(), key = lambda k: values[k])
        self.listbox.Set( ['<All>'] + values )
        self.listbox.SetSelection(0)
        self.PostEvent('<All>')


    def PostEvent(self, selection):
        evt = FieldPaneEvent(selection=selection, pane=self)
        wx.PostEvent(self.GetEventHandler(), evt)

    def SetEntries(self, entries):
        self.entries = entries
        self.UpdateListBox()
        
    def SetField(self, field):
        self.field = field.lower()
        self.choice.SetStringSelection(field)
        self.UpdateListBox()

    def OnFieldChange(self, evt):
        self.SetField(evt.GetString())
        evt.Skip()

    def OnListSelect(self, evt):
        self.PostEvent(evt.GetString())


# wxPython Phoenix: Use wx.lib.newevent
# The NewEvent() function returns an event class that can be instantiated with keyword arguments
FieldPaneEvent, EVT_FIELD_PANE = wx.lib.newevent.NewEvent()

# wxPython Phoenix: Use wx.lib.newevent
_DatabaseEvent, EVT_DATABASE = wx.lib.newevent.NewEvent()

class DatabaseEvent:
    """Helper class for posting database events."""
    
    @staticmethod
    def post_updated(obj, database):
        evt = _DatabaseEvent(database=database)
        wx.PostEvent(obj.GetEventHandler(), evt)

#-------------------------------------------------------------------------------
# Field Pane Panel
#-------------------------------------------------------------------------------
class FieldPanePanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, wx.ID_ANY)

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.panes = []
        for i, field in enumerate(['Genre', 'Artist', 'Album']):
            pane = FieldPane(self)
            self.panes.append(pane)
            pane.SetField(field)
            pane.Bind(EVT_FIELD_PANE, self.OnPaneSelect(i))
            sizer.Add(pane, 1, wx.ALL | wx.EXPAND, 5)

        choice = wx.Choice(self, wx.ID_ANY, choices=['Title'])
        choice.SetSelection(0)
        self.titlepane = wx.ListBox(self, wx.ID_ANY,
                                    style = wx.LB_SINGLE | wx.LB_SORT)
        s = wx.BoxSizer(wx.VERTICAL)
        s.Add(choice, 0, wx.ALL | wx.EXPAND, 5)
        s.Add(self.titlepane, 1, wx.ALL | wx.EXPAND, 5)
        sizer.Add(s, 1, wx.ALL | wx.EXPAND, 5)

        self.tagnavi = wx.TextCtrl(self, wx.ID_ANY, style = wx.TE_READONLY)
        tagnavisizer = wx.BoxSizer(wx.HORIZONTAL)
        tagnavisizer.Add(wx.StaticText(self, wx.ID_ANY, 'Tagnavi line:'), 0, wx.ALL | wx.ALIGN_CENTER, 5)
        tagnavisizer.Add(self.tagnavi, 1, wx.ALL | wx.EXPAND, 5)

        mainsizer = wx.BoxSizer(wx.VERTICAL)
        mainsizer.Add(sizer, 1, wx.EXPAND, 0)
        mainsizer.Add(tagnavisizer, 0, wx.EXPAND, 0)

        self.SetSizerAndFit(mainsizer)
        self.database = None

        self.OnFieldChange(None)
        self.Bind(EVT_DATABASE, self.OnDatabaseUpdate)
        self.Bind(wx.EVT_CHOICE, self.OnFieldChange)

    def OnFieldChange(self, evt):
        field_names = [pane.choice.GetStringSelection() for pane in self.panes]
        field_names = [name for name in field_names if name != '<None>']

        fields = [f.lower().replace(' ', '') for f in field_names]
        
        tagnavi = '"%s" -> %s ' % (field_names[0], fields[0])
        if self.database is not None:
            tagnavi += '? '
            for multiple_field in self.database.multiple_fields:
                if multiple_field in fields:
                    tagnavi += '%s != "<BLANK>" ' % multiple_field
                else:
                    tagnavi += '%s == "<BLANK>" ' % multiple_field

        for field in fields[1:]:
            tagnavi += '-> %s ' % field

        tagnavi += '-> title = "fmt_title"'

        self.tagnavi.ChangeValue(tagnavi)

    def OnDatabaseUpdate(self, evt):
        self.SetDatabase(evt.database)
        self.OnFieldChange(None)

    def SetDatabase(self, database):
        self.database = database
        self.panes[0].SetEntries(database.index.entries)

    def OnPaneSelect(self, pane_number):
        def func(evt):
            field = evt.pane.field
            entries = evt.pane.entries
            if evt.selection != '<All>':
                entries = [entry for entry in entries
                                if entry[field].matches(evt.selection) ]

            if pane_number == len(self.panes) - 1:
                # Special formatting for the title pane
                formatted = []
                for entry in entries:
                    format = ''
                    if entry['discnumber']:
                        format = '%d.' % entry['discnumber']
                    format += '%02d - %s' % \
                        (entry['tracknumber'], entry['title'].data)
                    formatted.append(format)
                self.titlepane.Set(formatted)
                return

            self.panes[pane_number + 1].SetEntries(entries)

        return func


class MyApp(wx.App):
    """Main wxPython application class."""
    
    def OnInit(self) -> bool:
        self.frame = MyFrame(None)
        return True


def main():
    """Main entry point for the Rockbox Database Manager GUI."""
    app = MyApp(redirect=False)
    app.MainLoop()
    # Kill any remaining threads before we're done.
    sys.exit()


if __name__ == "__main__":
    main()
