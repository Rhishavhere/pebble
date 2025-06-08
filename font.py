# find_fonts.py
import tkinter
from tkinter import font

# Create a root window (it won't be shown)
root = tkinter.Tk()

# Get a list of all font families
available_fonts = font.families()

# Print them, sorted alphabetically
for f in sorted(available_fonts):
    print(f)

# You can destroy the root window if you want, though it's not strictly necessary for this script
root.destroy()