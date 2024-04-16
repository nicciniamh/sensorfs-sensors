# Sensors
This is a demonstration of using my SensorFS and RestAPI to collect and display data using Gtk 
*Warning* I suck at Python GTK programming! 

I have tested this on my Raspberry Pi4 but mainly run this on macOS Sonoma. This likely will not 
run on your system without teaking paths and creating ramdisks. 

## General Desctiption
There are two components: First is get-data.py which forks and runs in background. If the daemon isn't 
started when the main app runs, the daemon is started automatically.

The main program presents a window with icons representing each defined sensors. Buttons on a toolbar 
allow app and sensor configuration. (changes to this will be reflected on the daemon)

Double-clicking an icon brings up a detail window. If there is already a detail window open, that window is raised.

Icons can be sorted by name or type in ascending or descending direction. 
