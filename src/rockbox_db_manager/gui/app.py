"""Application entry point for the Rockbox Database Manager GUI.

This module provides the wxPython application class and main entry point.
"""

import sys
import wx

from .main_frame import MyFrame


class MyApp(wx.App):
    """Main wxPython application class."""

    def OnInit(self) -> bool:
        """Initialize the application.
        
        Returns:
            True if initialization succeeded
        """
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
