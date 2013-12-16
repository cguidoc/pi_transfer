#!/usr/bin/python

# East Branch Engineering and Mfg, Inc
# Machine DNC system - network to Rs232 bridge
# Version 1.0 (RGB LCD Pi Plate with usb Serial Adaptor)
#	- Rewrite using simpler menu system
#		- remove xml dependencies
#		- display menu now hard coded
#	- Rewrite removing as many "local" variables as possible
#	- Added snake_case and CamelCase conventions
#	- made code more readable with better comments and section headers
# December 16, 2013
# Written by Chris Guidotti

# based on code from AdaFruit Industries (www.AdaFruit.com)
# AdaFruit   - https://github.com/adafruit/Adafruit-Raspberry-Pi-Python-Code.git, Adafruit_CharLCDPlate

# Use snake_case for variable names
# Use CamelCase for function names

# -----------------------------------------------------
# hardware usage
# 	- use up and down buttons to naviage up and down the menus
# 	- use select button to select choice
# 	- use left button to "escape" back a menu
# 
# 	- USB to Serial Adaptor should be plugged in
# -----------------------------------------------------


# Dependencies
import commands
from string 					import split
from time 						import sleep, strftime, localtime, time
from Adafruit_I2C 				import Adafruit_I2C
from Adafruit_MCP230xx 			import Adafruit_MCP230XX
from Adafruit_CharLCDPlate 		import Adafruit_CharLCDPlate

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
web_folder_location = '/var/www/Pi_web/data/'			# Data location of the website
web_queued = web_folder_location + 'queued/'			# Directory for files queued to transfer

# Global Variables
machine_log = web_folder_location + 'machine_log.txt'	# Log File
web_serial_config = web_folder_location + 'wconfig.txt'	# Serial parameters from website
machine_serial_config = 's_config.txt'					# "local" serial config parameters	
received_from_machine = 'from_machine.txt'				# file for receiving from serial			
serial_config = ConfigParser.RawConfigParser()			# Serial Parameter Parser object
main_menu = (
	('Send File 			\n 	to machine', 'SendFile()'),
	('Receive File 			\n 	from machine', 'ReceiveFile()'),
	('Setup 				\n 	(advanced)', 'DisplaySetupMenu()'))
setup_menu = (
	('1. Display time 	\n 	& IP Address', 'DisplayIP()'),
	('2. Load Serial 	\n 	from website', 'UpdateSerial()'),
	('3. System 			\n 	Shutdown!', 'ShutdownSys()'),
	('4. System 			\n 	Test hrdware', 'TestHardware()'))
queued_list = []
DISPLAY_ROWS = 2 										# Number of LCD Rows
DISPLAY_COLS = 16										# Number of LCD Columns
DEBUG = 1												# set DEBUG=1 to print debug statements

# initialize the LCD plate  
#   use busnum = 0 for raspi version 1 (256MB)   
#   and busnum = 1 for raspi version 2 (512MB)  
LCD = Adafruit_CharLCDPlate()

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
		print "==create_serial function=="
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
	write_to_log(message)
	message = "           port = " + serial_config.get('serial', 'port')
	write_to_log(message)
	message = "       baudrate = " + serial_config.get('serial', 'baudrate')
	write_to_log(message)
	message = "       bytesize = " + serial_config.get('serial', 'bytesize')
	write_to_log(message)
	message = "       stopbits = " + serial_config.get('serial', 'stopbits')
	write_to_log(message)
	message = "         parity = " + serial_config.get('serial', 'parity')
	write_to_log(message)
	message = "        xonxoff = " + serial_config.get('serial', 'xonxoff')
	write_to_log(message)
	
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

	if DEBUG:
		print "==file iterator function=="
	return_line = ""		# string to return
	with open (file, 'r') as f:
		file_string = f.read()	# read the file into a string
		
		for line in file_string.splitlines():
			if character in line:
				return_line = line.split(character)[1]
				break
	if DEBUG:
		print "  " + return_line
	return return_line

def TestHardware():
	col = (('Red' , lcd.RED) , ('Yellow', lcd.YELLOW), ('Green' , lcd.GREEN),
           ('Teal', lcd.TEAL), ('Blue'  , lcd.BLUE)  , ('Violet', lcd.VIOLET),
           ('Off' , lcd.OFF) , ('On'    , lcd.ON))

    for c in col:
       if DEBUG
       		print "hardware test | " + c[0]
	   lcd.clear()
       lcd.message(c[0])
       lcd.backlight(c[1])
       sleep(0.5)

def ReadButton():  
   button = LCD.buttonPressed()  
   # Debounce push buttons  
   if(button != 0):  
      while(LCD.buttonPressed() != 0):  
         DelayMilliseconds(1)  
   return buttons

def DelayMilliseconds(milliseconds):  
   seconds = milliseconds / float(1000) # divide milliseconds by 1000 for seconds  
   sleep(seconds)
  
def DisplaySetupMenu():
	keep_looping = True
	menu_loc = 0
	lcd.message(setup_menu[menu_loc])

	while keep_looping:
        press = ReadButton()

        #Left Button Pressed
        if(press == lcd.LEFT):

        #Right Button Pressed
        if(press == lcd.RIGHT):
        	if (menu_loc == 0)


        #UP Botton Pressed
        if(press == lcd.UP):
        	menu_loc += -1
        	lcd.message(setup_menu[menu_loc])

        #DOWN Button Pressed
        if(press == lcd.DOWN):
        	menu_loc += 1
        	lcd.message(menu[menu_loc])

        #Select Button Pressed
        if(press == lcd.SELECT):

# ------------------------------------------------
# --  MAIN FUNCTIONS
# ------------------------------------------------
def main():
	LCD.begin(DISPLAY_COLS, DISPLAY_ROWS)
	lcd.backlight(lcd.ON)
	TestHardware()
	lcd.message("East Branch Eng\nDNC System V1.0")
    sleep(1)    

    menu_loc = 0
    lcd.clear()
    lcd.message(main_menu[menu_loc])
    
    while True:
        press = ReadButton()
        
        #Right Button Pressed
        if(press == lcd.RIGHT):
        	if DEBUG:
        		print "Right Button Pressed - Do nothing"
        	
        	

        #UP Botton Pressed
        if(press == lcd.UP):
        	menu_loc += -1
        	if (menu_loc < 0):
        		menu_loc = len(main_menu)
        	lcd.message(menu[menu_loc][0])
        	if DEBUG:
        		print main_menu[menu_loc][0]

        #DOWN Button Pressed
        if(press == lcd.DOWN):
        	menu_loc += 1
        	if (menu_loc > len(main_menu)):
        		menu_loc = 0 	#roll over
        	lcd.message(menu[menu_loc][0])
        	if DEBUG:
        		print main_menu[menu_loc][0]


        #Select Button Pressed
        if(press == lcd.SELECT):
        	if DEBUG:
        		print main_menu[menu_loc][0]
        	exec main_menu[menu_loc][1]
        

   