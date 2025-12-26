import wx
import wx.lib.newevent
import functools
import threading
import sys
from typing import Callable, Optional, Any

from .database import Database
from .defs import FORMATTED_TAGS
from . import wxFB_gui


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
    def post_start(obj):
        evt = ThreadStartEvent()
        wx.PostEvent(obj.GetEventHandler(), evt)

    @staticmethod
    def post_end(obj):
        evt = ThreadEndEvent()
        wx.PostEvent(obj.GetEventHandler(), evt)

    @staticmethod
    def post_callback(obj, message, *args, **kwargs):
        evt = ThreadCallbackEvent(message=message, args=args, **kwargs)
        wx.PostEvent(obj.GetEventHandler(), evt)


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
                self.time = s

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
        self.panes = FieldPanePanel(self.notebook)
        self.notebook.AddPage(self.panes, 'View')
        self.status.SetStatusWidths([200,-1])

        # Insert the info panel into the sizer
        self.infopanel = InfoPanel(self.mainpanel)
        self.mainpanel.GetSizer().Insert(0, self.infopanel, 1, wx.ALL | wx.EXPAND, 5)
        self.mainpanel.Layout()

        self.database = Database()
        self.message_callback = functools.partial(
            ThreadEvent.post_callback, self
        )

        self.thread_info = [] # List of currently running info panels

        self.Show()

        self.Bind(wx.EVT_CLOSE, self.OnClose)

    def OnLoadTags(self, evt):
        filename = wx.FileSelector('Load Tags', default_extension='.pkl')
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

        self.start_thread(
            self.database.load_tags,
                filename,
                callback = self.message_callback,
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

        self.start_thread(
            self.database.save_tags,
                filename,
                callback = self.message_callback,
            _start=OnStart, _message=OnMessage, _end=OnEnd,
            _info = self.infopanel.MakeRow('Saving tags')
        )

    def OnAddDirectory(self, evt):
        dir = wx.DirSelector('Music Directory')
        if not dir:
            return

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

        self.start_thread(
            self.database.add_dir,
                dir,
                dircallback = None,
                filecallback = self.message_callback,
                estimatecallback = self.message_callback,
            _start=OnStart, _message=OnMessage, _end=OnEnd,
            _info = self.infopanel.MakeRow('Adding %s' % dir)
        )

    def OnGenerateDatabase(self, evt):
        # Make the formats
        for field in FORMATTED_TAGS:
            format = self.__dict__[field.replace(' ','')].GetValue()
            sort   = self.__dict__[field.replace(' ','')+'_sort'].GetValue()
            self.database.set_format(field, format, sort)

        def OnStart(evt):
            evt.info.timer.Start()
            evt.info.SetRange(len(self.database.paths))
        def OnMessage(evt):
            evt.info.status = evt.message
            evt.info.gauge += 1
        def OnEnd(evt):
            evt.info.timer.Stop()
            evt.info.status = 'Done'
            DatabaseEvent.post_updated(self.panes, self.database)

        self.start_thread(
            self.database.generate_database,
                callback = self.message_callback,
            _start=OnStart, _message=OnMessage, _end=OnEnd,
            _info = self.infopanel.MakeRow('Generating database')
        )

    def OnWriteDatabase(self, evt):
        write_dir = wx.DirSelector('Database Output Directory')
        if not write_dir:
            return

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
            DatabaseEvent.post_updated(self.panes, self.database)

        self.start_thread(
            self.database.write,
                write_dir,
                callback = self.message_callback,
            _start=OnStart, _message=OnMessage, _end=OnEnd,
            _info = self.infopanel.MakeRow('Writing database')
        )

    def OnReadDatabase(self, evt):
        read_dir = wx.DirSelector('Database Directory')
        if not read_dir:
            return

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
            DatabaseEvent.post_updated(self.panes, self.database)

        def read_database(directory, callback=None):
            self.database = Database.read(directory, callback)

        self.start_thread(
            read_database,
                read_dir,
                callback = self.message_callback,
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
        end: Callable = kwargs.pop('_end', lambda evt: None)
        start: Optional[Callable] = kwargs.pop('_start', None)
        message: Optional[Callable] = kwargs.pop('_message', None)
        info = kwargs.pop('_info', None)
        
        if info is not None:
            self.thread_info.append(info)

        # Worker function that will be called in the thread
        def worker() -> None:
            try:
                if start:
                    def start_func(evt: Any) -> None:
                        evt.info = info
                        start(evt)
                        self.Unbind(EVT_THREAD_START, None)
                    self.Bind(EVT_THREAD_START, start_func)
                    ThreadEvent.post_start(self)

                if message:
                    def message_func(evt: Any) -> None:
                        evt.info = info
                        message(evt)
                    self.Bind(EVT_THREAD_CALLBACK, message_func)

                # Execute the actual function
                func(*args, **kwargs)

                def end_func(evt: Any) -> None:
                    evt.info = info
                    end(evt)
                    self.Unbind(EVT_THREAD_END, None)
                    if message:
                        self.Unbind(EVT_THREAD_CALLBACK, None)
                    if info in self.thread_info:
                        self.thread_info.remove(info)
                self.Bind(EVT_THREAD_END, end_func)
                ThreadEvent.post_end(self)

            except SystemExit:
                # Allow clean thread termination
                pass
            except Exception as e:
                # Log any unexpected errors
                print(f"Thread error: {e}", file=sys.stderr)

        # Create and start the daemon thread
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()


    def OnClose(self, evt):
        # I haven't bothered to make a nice way to stop the threads, so just
        # make sure that the events they send aren't caught by the frame
        # after it is destroyed.

        # Unbind all of the events we recieve so we aren't trying to send
        # events to a dead window.
        for info in self.thread_info:
            info.timer.Stop()
        self.Unbind(EVT_THREAD_START, None)
        self.Unbind(EVT_THREAD_CALLBACK, None)
        self.Unbind(EVT_THREAD_END, None)
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
