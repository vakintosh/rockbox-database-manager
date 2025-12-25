#!/usr/bin/env python
# Quick test to see if gui.pyw imports work
import sys
print("Testing imports...")

try:
    import wx
    print("✓ wx imported")
except Exception as e:
    print("✗ wx import failed:", e)
    sys.exit(1)

try:
    from database import Database
    print("✓ Database imported")
except Exception as e:
    print("✗ Database import failed:", e)
    sys.exit(1)

try:
    from defs import ENCODING, FORMATTED_TAGS
    print("✓ defs imported")
except Exception as e:
    print("✗ defs import failed:", e)
    sys.exit(1)

try:
    import wxFB_gui
    print("✓ wxFB_gui imported")
except Exception as e:
    print("✗ wxFB_gui import failed:", e)
    sys.exit(1)

print("\nAll imports successful!")
print("\nNow creating wx.App...")

try:
    app = wx.App(False)  # Don't redirect output
    print("✓ App created")
except Exception as e:
    print("✗ App creation failed:", e)
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\nNow importing MyFrame from gui.pyw...")
try:
    # Import the frame class from gui
    import importlib.util
    spec = importlib.util.spec_from_file_location("gui_module", "gui.pyw")
    gui_module = importlib.util.module_from_spec(spec)
    
    # Execute only the imports and class definitions, not the main app
    with open('gui.pyw', 'r') as f:
        code = f.read()
        # Remove the app creation at the end
        code = code.replace('app = MyApp(redirect = True)', '# app = MyApp(redirect = True)')
        code = code.replace('app.MainLoop()', '# app.MainLoop()')
        code = code.replace('sys.exit()', '# sys.exit()')
        exec(code, globals())
    
    print("✓ GUI module loaded")
except Exception as e:
    print("✗ GUI module load failed:", e)
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\nNow creating MyFrame...")
try:
    frame = MyFrame(None)
    print("✓ Frame created")
    print(f"✓ Frame.Show() returned: {frame.Show()}")
    print("✓ Frame is shown:", frame.IsShown())
    print("✓ Frame position:", frame.GetPosition())
    print("✓ Frame size:", frame.GetSize())
except Exception as e:
    print("✗ Frame creation failed:", e)
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n✓✓✓ Everything initialized successfully!")
print("Starting MainLoop... (window should appear)")
print("Close the window to exit.")

app.MainLoop()
