#!/usr/bin/python

# East Branch Engineering and Mfg, Inc
# Machine DNC system - network to Rs232 bridge
# Version 1.0 (RGB LCD Pi Plate with usb Serial Adaptor)
#   - Rewrite using simpler menu system
#       - remove xml dependencies
#       - display menu now hard coded
#   - Rewrite removing as many "local" variables as possible
#   - Added snake_case and CamelCase conventions
#   - made code more readable with better comments and section headers
# December 16, 2013
# Written by Chris Guidotti

# based on code from AdaFruit Industries (www.AdaFruit.com)
# AdaFruit   - https://github.com/adafruit/Adafruit-Raspberry-Pi-Python-Code.git, Adafruit_CharLCDPlate

# Use snake_case for variable names
# Use CamelCase for function names

# -----------------------------------------------------
# hardware usage
#   - use up and down buttons to naviage up and down the menus
#   - use select button to select choice
#   - use left button to "escape" back a menu
# 
#   - USB to Serial Adaptor should be plugged in
# -----------------------------------------------------


# Dependencies
import commands
from string                     import split
from time                       import sleep, strftime, localtime, time
from Adafruit_I2C               import Adafruit_I2C
from Adafruit_MCP230xx          import Adafruit_MCP230XX
from Adafruit_CharLCDPlate      import Adafruit_CharLCDPlate

import ConfigParser
import ast
import serial
import time
import string
import smbus
import shutil
import os
import glob


# Global Directories
web_folder_location = '/var/www/Pi_web/data/'                       # Data location of the website
web_queued = web_folder_location + 'queued/'                        # Directory for files queued to transfer

# Global Variables
machine_log = web_folder_location + 'machine_log.txt'               # Log File
web_serial_config = web_folder_location + 'wconfig.txt'             # Serial parameters from website
machine_serial_config = 's_config.txt'                              # "local" serial config parameters  
received_from_machine = web_folder_location + 'from_machine.txt'    # file for receiving from serial            
serial_config = ConfigParser.RawConfigParser()                      # Serial Parameter Parser object
main_menu = [
	['Send File\nto machine', 'Send()'],
	['Receive File\nfrom machine', 'ReceiveFile()'],
	['Setup\n(advanced)', 'DisplayMenu(setup_menu)']]
setup_menu = [
	['1. Show IP\n  & Address', 'ShowIPAddress()'],
	['2. Load Serial\n  from website', 'UpdateSerial()'],
	['3. System\n  Shutdown!', 'ShutdownSys()'],
	['4. System\n  Test hrdware', 'TestHardware()']]
queued_list = []
DISPLAY_ROWS = 2                                        # Number of LCD Rows
DISPLAY_COLS = 16                                       # Number of LCD Columns
DEBUG = 1                                               # set DEBUG=1 to print debug statements

# initialize the LCD plate  
#   use busnum = 0 for raspi version 1 (256MB)   
#   and busnum = 1 for raspi version 2 (512MB)  
lcd = Adafruit_CharLCDPlate()

# in case you add custom logic to lcd to check if it is connected (useful)
#if lcd.connected == 0:
#    quit()


# ------------------------------------------------
# --  HELPER FUNCTIONS
# ------------------------------------------------
def WriteToLog(entry):
	entry = strftime("%Y-%m-%d %H:%M:%S", localtime()) + " - " + entry + "\n"
	with open(machine_log, 'a+') as f:
		f.write(entry)
	if DEBUG:
		print "**Log file updated**"

def CreateSerial():
	#returns a serial object with the serial parameters from config file
	if DEBUG:
		print "==CreateSerial function=="
	#update serial config parameters using config parser
	serial_config.read(machine_serial_config)
	if DEBUG:
		print "  serial parameters read from file"
		print "      port = " + serial_config.get('serial', 'port')
		print "  baudrate = " + serial_config.get('serial', 'baudrate')
		print "  bytesize = " + serial_config.get('serial', 'bytesize')
		print "  stopbits = " + serial_config.get('serial', 'stopbits')
		print "    parity = " + serial_config.get('serial', 'parity')
		print "   xonxoff = " + serial_config.get('serial', 'xonxoff')
	# Update log file with new serial parameters for troubleshooting on machines
	message = "  -- serial parameters read from file --"
	WriteToLog(message)
	message = "           port = " + serial_config.get('serial', 'port')
	WriteToLog(message)
	message = "       baudrate = " + serial_config.get('serial', 'baudrate')
	WriteToLog(message)
	message = "       bytesize = " + serial_config.get('serial', 'bytesize')
	WriteToLog(message)
	message = "       stopbits = " + serial_config.get('serial', 'stopbits')
	WriteToLog(message)
	message = "         parity = " + serial_config.get('serial', 'parity')
	WriteToLog(message)
	message = "        xonxoff = " + serial_config.get('serial', 'xonxoff')
	WriteToLog(message)
	
	return serial.Serial(
		port = serial_config.get('serial', 'port'),
		baudrate = serial_config.get('serial', 'baudrate'),
		bytesize = serial_config.getint('serial', 'bytesize'),
		stopbits = serial_config.getint('serial', 'stopbits'),
		parity = serial_config.get('serial', 'parity'),
		xonxoff = serial_config.getboolean('serial', 'xonxoff'))
	
def FileAccessable(filepath, mode):
	# check if file exists and is accessable with selected mode
	# use this function to check if file exists and capture IO errors so program doesn't halt
	# returns bool
	try:
		f = open(filepath, mode)
	except IOError as e:
		return False
	return True
	
def FileIterator(file, character):
	# takes file and iterates line by line until character is found
	# returns the portion of the string after the character, 
	# if no string is found, returns an empty string
	return_line = ""        # string to return
	with open (file, 'r') as f:
		file_string = f.read()  # read the file into a string
		
		for line in file_string.splitlines():
			if character in line:
				return_line = line.split(character)[1]
				break
	if DEBUG:
		print "  " + return_line
	return return_line

def TestHardware():
	if DEBUG:
		print "==TestHardware function=="
	col = (('Red' , lcd.RED) , ('Yellow', lcd.YELLOW), ('Green' , lcd.GREEN),
		('Teal', lcd.TEAL), ('Blue'  , lcd.BLUE)  , ('Violet', lcd.VIOLET),
		('Off' , lcd.OFF) , ('On'    , lcd.ON))

	for c in col:
		if DEBUG:
			print " - hardware test | " + c[0]
		lcd.clear()
		lcd.message(c[0])
		lcd.backlight(c[1])
		sleep(0.5)

def ReadLCDButton():
	if DEBUG:
		print "==ReadButton function=="  
	button = lcd.buttons()
	# Debounce push buttons
	if(button != 0):
		while(lcd.buttons() != 0):
			DelayMilliseconds(1)
	return button

def DelayMilliseconds(milliseconds):
	seconds = milliseconds / float(1000) # divide milliseconds by 1000 for seconds
	sleep(seconds)
  
def DisplayMenu(menu):
	if DEBUG:
		print "==DisplayMenu function=="
	keep_looping = True
	menu_loc = 0
	prev = 0
	lcd.message(menu[menu_loc][0])
	if DEBUG:
		print " - " + menu[menu_loc][0]

	while keep_looping:
		sleep(.25)				#delay a bit to debounce the switch
		
		#Left Button Pressed
		if(lcd.buttonPressed(lcd.LEFT)):
			if DEBUG:
				print " - left button pressed - escaping menu"
			lcd.clear()
			keep_looping = False

		#Right Button Pressed
		if(lcd.buttonPressed(lcd.RIGHT)):
			if DEBUG:
				print " -  right button pressed - do nothing"
			
		#UP Botton Pressed
		if(lcd.buttonPressed(lcd.UP)):
			if DEBUG:
				print " - up button pressed - move menu"
			prev = menu_loc
			menu_loc += -1
			if (menu_loc < 0):
				menu_loc = (len(menu)-1)
			lcd.clear()
			lcd.message(menu[menu_loc][0])			

		#DOWN Button Pressed
		if(lcd.buttonPressed(lcd.DOWN)):
			if DEBUG:
				print " - down button pressed - move menu"
			prev = menu_loc
			menu_loc += 1
			if (menu_loc > (len(menu)-1)):
				menu_loc = 0
			lcd.clear()
			lcd.message(menu[menu_loc][0])

		#Select Button Pressed
		if(lcd.buttonPressed(lcd.SELECT)):
			if DEBUG:
				print " - select button pressed - select item"
			exec menu[menu_loc][1]
		
			
		

def ShowIPAddress():
	if DEBUG:
		print('==ShowIPAddress function==')
	lcd.clear()
	lcd.message(commands.getoutput("/sbin/ifconfig").split("\n")[1].split()[1][5:])
	while 1:
		if lcd.buttonPressed(lcd.LEFT):
			break
		sleep(0.25)

def UpdateSerial():
	#update serial parameters from config file loaded from webserver
	if DEBUG:
		print "==UpdateSerial function=="
	lcd.clear()
	lcd.message('Are you sure?\nPress Sel for Y')
	while 1:
		if (lcd.buttonPressed(lcd.LEFT)):
			break
		if (lcd.buttonPressed(lcd.SELECT)):
			lcd.clear()
			lcd.backlight(lcd.RED)
			if DEBUG:
				print "  --web file located at--"
				print "  " + web_serial_config + "\n"
			if FileAccessable(web_serial_config, "r"):
				if DEBUG:
					print " - new web config found"
					print " - attempting to copy..."
				lcd.message('new file found\nattempting copy')              
				if DEBUG:
					print "  ...file copied\n"
				lcd.clear()
				lcd.message('...file copied')
				shutil.copy(web_serial_config, machine_serial_config) 
				#create serial object to test new file      
				CreateSerial()
				if DEBUG:
					print " - serial object created to test new parameters"
				WriteToLog("NOTICE: new serial parameters updated from web")
				lcd.backlight(lcd.GREEN)
				break
			else:
				if DEBUG:
					print "  file not found or not accessible"
				lcd.clear()
				lcd.message('file not found\nor no permission')
				sleep(5)
				WriteToLog("ERROR: Serial parameters not updated from web - file access error")
				lcd.backlight(lcd.GREEN)
				break

def ShutdownSys():
	if DEBUG:
		print "==ShutdownSys function=="
	lcd.clear()
	lcd.message('Are you sure?\nPress Sel for Y')
	while 1:
		if lcd.buttonPressed(lcd.LEFT):
			break
		if lcd.buttonPressed(lcd.SELECT):
			lcd.clear()
			lcd.backlight(lcd.OFF)
			commands.getoutput("sudo shutdown -h now")
			quit()
		sleep(0.25)

def Send():
	if DEBUG:
		print "==Send function=="
	lcd.clear()
	lcd.backlight(lcd.RED)
	WriteToLog("NOTICE: attempting to send a file to the machine")
	WriteToLog(" - Fetching list of new files...")
	lcd.message("fetching files...")
	#create a list of programs in the data directory            

	path = web_queued + '*.txt'
	file_list = glob.glob(path)
	if DEBUG:
		print " - directory crawled"
	for file in file_list:
		widget = [FileIterator(file, ":")]
		widget.append('SendFile("' + file + '")')
		queued_list.append(widget)
		if DEBUG:
			print widget
			print " - file: " + widget[-1][0] + "added"
		message = " - file: " + widget[-1][0] + "added to list of files"
		WriteToLog(message)
	if DEBUG:
		print " - queued list updated"
	lcd.clear()
	lcd.message("file list updated")
	sleep(.5)
	lcd.clear()
	lcd.backlight(lcd.VIOLET)
	lcd.message("pick file")
	DisplayMenu(queued_list)
	lcd.backlight(lcd.GREEN)

	
def SendFile(file):
	if DEBUG:
		print "==SendFIle function=="
		print "  - send " + file + " to machine using rs232"
	if FileAccessable(file,"r"):
		if DEBUG:
			print " - opening the file and converting to string"
		lcd.clear()
		lcd.message("converting...")
		file_handle = open (file, 'r')
		data = file_handle.read()
		file_handle.close()
		if DEBUG:
			print " - file converted"
		lcd.clear()
		lcd.message("...file converted")

		#open serial object
		ser = CreateSerial()
		if DEBUG:
			print " - serial object created"
		lcd.clear()
		lcd.message("opening port..")
		ser.close()
		if DEBUG:
			print " - serial object closed"
		ser.open()
		if DEBUG:
			print " - serial object re-openend"

		#if the serial port is open, send the data string
		if DEBUG:
			print " - sending data..."
		lcd.clear()
		lcd.message("sending...")
		if ser.isOpen():                
			ser.write(data)
			if DEBUG:
				print " - data sent"
			ser.close()
			if DEBUG:
				print " - object closed"
		lcd.clear()
		lcd.message("data sent!")
		sleep(1)
		WriteToLog("NOTICE: file successfully sent to machine")
		lcd.backlight(lcd.GREEN)
			

def ReceiveFile():
	if DEBUG:
		print "==ReceiveFile function=="
	lcd.clear()
	lcd.message('Are you sure?\nPress Sel for Y')
	while 1:
		if lcd.buttonPressed(lcd.LEFT):
			break
		if lcd.buttonPressed(lcd.SELECT):
			lcd.clear()
			lcd.backlight(lcd.RED)
			try:
				rfile = open(received_from_machine, 'w+')
				if DEBUG:
					print " - creating receiving file"
			except OSError:
				lcd.message("error w file")
				if DEBUG:
					print " - error creating file"
				return False

	
		ser = CreateSerial()
		if DEBUG:
			print " - serial object created"
		lcd.clear()
		lcd.message("opening port...")
		ser.close()
		if DEBUG:
			print " - serial object closed"
		ser.open()
		if DEBUG:
			print " - serial object re-openend"
			print " - receiving data..."
		lcd.clear()
		lcd.message("receiving...")
		if ser.isOpen():
			timeout=1
			lines = []
			while True:
				line = ser.readline()
				lines.append(line.decode('utf-8').rstrip())

				# wait for new data after each line
				timeout = time.time() + 0.1
				while not ser.inWaiting() and timeout > time.time():
					pass
				if not ser.inWaiting():
					break                 
		if DEBUG:
			print " - ...data received"
		ser.close()
		if DEBUG:
			print " - serial object closed"
		lcd.clear()
		lcd.message("data received")
		data = string.join(lines, "\n")
		if DEBUG:
			print " - converting data array to string"
		lcd.clear()
		lcd.message("data converted")
		rfile.write(data)
		if DEBUG:
			print " - writing data to file"
		rfile.close()
		if DEBUG:
			print " - closing file"
		lcd.clear()
		lcd.message("data saved") 
		sleep(1)   
		lcd.backlight(lcd.GREEN)
		WriteToLog("NOTICE: file sucessfully received from machine")
		break



# ------------------------------------------------
# --  MAIN FUNCTIONS
# ------------------------------------------------
def main():
	lcd.begin(DISPLAY_COLS, DISPLAY_ROWS)
	lcd.backlight(lcd.ON)
	TestHardware()
	lcd.message("East Branch Eng\nDNC System V1.0")
	sleep(1)    

	menu_loc = 0
	prev = 0
	lcd.clear()
	lcd.backlight(lcd.GREEN)
	lcd.message(main_menu[menu_loc])
	
	while True:
		sleep(.25)
			
		#Right Button Pressed
		if(lcd.buttonPressed(lcd.RIGHT)):
			if DEBUG:
				print " - Right Button Pressed - Do nothing"

		#UP Botton Pressed
		if(lcd.buttonPressed(lcd.UP)):
			menu_loc += -1
			if (menu_loc < 0):
				menu_loc = (len(main_menu)-1)
			lcd.clear()
			lcd.message(main_menu[menu_loc][0])
			if DEBUG:
				print " - Menu Location down | " + main_menu[menu_loc][0]

		#DOWN Button Pressed
		if(lcd.buttonPressed(lcd.DOWN)):
			menu_loc += 1
			if (menu_loc > (len(main_menu)-1)):
				menu_loc = 0    #roll over
			lcd.clear()
			lcd.message(main_menu[menu_loc][0])
			if DEBUG:
				print " - Menu Location up | " + main_menu[menu_loc][0]

		#Select Button Pressed
		if(lcd.buttonPressed(lcd.SELECT)):
			if DEBUG:
				print main_menu[menu_loc][0]
			exec main_menu[menu_loc][1]

if __name__ == '__main__':
	WriteToLog("System Initialized")
	main()
