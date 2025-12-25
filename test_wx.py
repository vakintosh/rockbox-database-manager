#!/usr/bin/env python
import sys
import wx

print("Python version:", sys.version)
print("wxPython version:", wx.version())
print("Platform:", wx.PlatformInfo)

app = wx.App(False)
frame = wx.Frame(None, wx.ID_ANY, "Test Window", size=(400, 300))
panel = wx.Panel(frame)
text = wx.StaticText(panel, label="Hello from wxPython!", pos=(50, 50))
frame.Show(True)
print("Window should now be visible!")
app.MainLoop()
