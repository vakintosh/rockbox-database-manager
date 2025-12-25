#!/bin/bash
# Diagnostic script for wxPython GUI issues on macOS

cd "$(dirname "$0")"

echo "=== Rockbox Database Manager GUI Diagnostic ==="
echo ""

echo "1. Checking Python version..."
.venv/bin/python --version

echo ""
echo "2. Checking if Python is framework-enabled..."
.venv/bin/python -c "import sysconfig; print('Framework:', sysconfig.get_config_var('PYTHONFRAMEWORK'))"

echo ""
echo "3. Checking wxPython installation..."
.venv/bin/python -c "import wx; print('wxPython version:', wx.version())"

echo ""
echo "4. Checking display environment..."
echo "DISPLAY=$DISPLAY"

echo ""
echo "5. Testing minimal wxPython app..."
.venv/bin/python -c "
import wx
import sys

print('Creating wx.App...')
app = wx.App(False)
print('App created successfully')

print('Creating frame...')
frame = wx.Frame(None, title='Test', size=(100,100))
print('Frame created')

print('Showing frame...')
result = frame.Show(True)
print('Show() returned:', result)

print('Starting MainLoop (this will block)...')
print('If you see a window, close it to continue.')
print('If no window appears after 5 seconds, press Ctrl+C')

# Run for a limited time
import threading
def quit_app():
    import time
    time.sleep(5)
    print('Timeout - exiting')
    app.ExitMainLoop()

thread = threading.Thread(target=quit_app)
thread.daemon = True
thread.start()

app.MainLoop()
print('MainLoop exited')
"

echo ""
echo "=== Diagnostic complete ==="
echo ""
echo "If you saw a test window appear and disappear, wxPython is working!"
echo "If not, there may be an issue with your macOS configuration."
