#!/usr/bin/python
#
# EBE Machine Bridge
# Provides a network to RS232 bridge to the machine tools
# Can use WiFi or hardwire for the connection
# Webserver provides a way to update serial configuration and upload files
# serial parameters are stored in a local file that is updated from the website
# 	 - for security and reliability the website does not automatically update serial parameters.
# Based on code from Adafruit and lan Aufderheide, February 2013
#
# This provides a menu driven application using the LCD Plates
# from Adafruit Electronics.
#
# version 0.1 - send and receive

#===Function List for machine bridge
# DoSend() - takes a file and sends it over RS232
# DoReceive() - receives a file from RS232
# UpdateSerial() - updates the serial configuration parameters from website


import commands
from string import split
from time import sleep, strftime, localtime, time
from xml.dom.minidom import *
from Adafruit_I2C import Adafruit_I2C
from Adafruit_MCP230xx import Adafruit_MCP230XX
from Adafruit_CharLCDPlate import Adafruit_CharLCDPlate
from ListSelector import ListSelector
import ConfigParser
import ast
import serial
import time
import string
import smbus
import shutil
import os
import glob

serial_config = ConfigParser.RawConfigParser()			# Serial Parameter Parser object

#===File Names and Locations===
configfile = 'lcdmenu.xml'								# LCD Menu Config file
queuedlist = 'queuedlist.xml'
web_folder_location = '/var/www/Pi_web/data/'			# Data location of the website
web_serial_config = web_folder_location + 'wconfig.txt'	# Serial parameters from website	
machine_transfer_to_server = 'from_machine.txt'			# file for receiving from serial
machine_serial_config = 's_config.txt'					# "local" serial config parameters				
machine_log = web_folder_location + 'machine_log.txt'	# Log File Location
machine_queued = 'to_machine.txt'						# internal queued file to transfer
web_queued = web_folder_location + '/queued'
current_location = '/home/pi/pi_transfer/'				# working directory

# set DEBUG=1 for print debug statements
DEBUG = 1
DISPLAY_ROWS = 2
DISPLAY_COLS = 16

# set busnum param to the correct value for your pi
lcd = Adafruit_CharLCDPlate()
# in case you add custom logic to lcd to check if it is connected (useful)
#if lcd.connected == 0:
#    quit()

lcd.begin(DISPLAY_COLS, DISPLAY_ROWS)
lcd.backlight(lcd.OFF)

#===MAIN FUNCTIONS===
# call these functions first to perform various tasks

def DoSend():
	if DEBUG:
		print "==DoSend function=="
	while 1:
		if lcd.buttonPressed(lcd.LEFT):
			break
		if lcd.buttonPressed(lcd.SELECT):
			lcd.clear()
			LcdRed()
			write_to_log("NOTICE: attempting to send a file to the machine")
			queued_list();	#create a list of programs in the data directory			
			file_uiItems = Folder('root','')
			file_dom = parse(queuedlist) # parse an XML file by name
			file_top = file_dom.documentElement
			ProcessNode(file_top, file_uiItems)
			file_display = Display(file_uiItems)
			file_display.display()
			sleep(1)
			while 1:
				if (lcd.buttonPressed(lcd.LEFT)):
				   break

				if (lcd.buttonPressed(lcd.UP)):
					file_display.update('u')
					file_display.display()

				if (lcd.buttonPressed(lcd.DOWN)):
					file_display.update('d')
					file_display.display()

				if (lcd.buttonPressed(lcd.SELECT)):
					file_display.update('s')
					file_display.display()
				sleep(.25)
			LcdGreen()
			break

def DoReceive():
	if DEBUG:
		print "==DoRec function=="
	lcd.clear()
	lcd.message('Are you sure?\nPress Sel for Y')
	while 1:
		if lcd.buttonPressed(lcd.LEFT):
			break
		if lcd.buttonPressed(lcd.SELECT):
			lcd.clear()
			LcdRed()
			xrec(machine_transfer_to_server)
			transfer(machine_transfer_to_server, web_folder_location)
			LcdGreen()
			write_to_log("NOTICE: file sucessfully received from machine")
			break

def UpdateSerial():
	#update serial parameters from config file loaded from webserver
	if DEBUG:
		print "==UpdateSerial function=="
	lcd.clear()
	lcd.message('Are you sure?\nPress Sel for Y')
	while 1:
		if lcd.buttonPressed(lcd.LEFT):
			break
		if lcd.buttonPressed(lcd.SELECT):
			lcd.clear()
			LcdRed()
			if DEBUG:
				print "  --web file located at--"
				print "  " + web_serial_config + "\n"
			if file_accessible(web_serial_config, "r"):
				if DEBUG:
					print "  new web config found"
					print "  attempting to copy..."
				lcd.message('new file found\nattempting copy')
				sleep(1)				
				if DEBUG:
					print "  ...file copied\n"
				lcd.clear()
				lcd.message('...file copied')
				sleep(1)
				shutil.copy(web_serial_config, machine_serial_config) 
				#create serial object to test new file		
				create_serial()
				if DEBUG:
					print "  serial object created to test new parameters"
				write_to_log("NOTICE: new serial parameters updated from web")
				LcdGreen()

				break
			else:
				if DEBUG:
					print "  file not found or not accessible"
				lcd.clear()
				lcd.message('file not found\nor no permission')
				sleep(5)
				write_to_log("ERROR: Serial parameters not updated from web - file access error")
				LcdGreen()
				break

#===HELPER FUNCTIONS===
# these are called by the main functions

def switchmenu():
	dom = parse(configfile) # parse an XML file by name
	top = dom.documentElement
	ProcessNode(top, uiItems)
	display.display()


def queued_list():
	# generates an xml file with the current list of files in the queued directory
	if DEBUG:
		print "==QUEUED LIST FUNCTION=="

	path = web_queued + '/*.txt'
	file_list = glob.glob(path)
	with open(queuedlist, 'a+') as f:
		f.truncate()
		f.write("<application>\n")
		for file in file_list:
			widget = '\t<widget text="' + file_iterator(file, ":") + '" function="xsend(\'' + file + '\')" />\n'
			f.write(widget)
		f.write("</application>\n")	
	if DEBUG:
		print "**queued list updated**"

def write_to_log(entry):
	entry = strftime("%Y-%m-%d %H:%M:%S", localtime()) + " - " + entry + "\n"
	with open(machine_log, 'a+') as f:
		f.write(entry)
	if DEBUG:
		print "**Log file updated**"

def create_serial():
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
	
def file_accessible(filepath, mode):
	# check if file exists and is accessable with selected mode
	# use this function to check if file exists and capture IO errors so program doesn't halt
	# returns bool
	try:
		f = open(filepath, mode)
	except IOError as e:
		return False
	return True
	
def file_iterator(file, character):
	# takes file and iterates line by line until character is found
	# returns the first string containing the character
	# if no string is found, returns an empty string

	if DEBUG:
		print "==file iterator function=="
	return_line = ""		# string to return
	with open (file, 'r') as f:
		file_string = f.read()	# read the file into a string
		
		for line in file_string.splitlines():
			if character in line:
				return_line = line
				break
	if DEBUG:
		print "  " + return_line
	return return_line

def transfer(filename, location):
	#transfer file to the location
	if DEBUG:
		print "==TRANSFER FUNCTION=="
		print "  " + filename + "-->" + location
	if file_accessible(filename, "r"):
		if DEBUG:
			print "  " + filename + " found"
		lcd.message('file found\nattempting move')
		sleep(1)		
		shutil.copy(filename, location)
		if DEBUG:
			print "  " + filename + "-->" + location + "...transfer done"
		lcd.clear()
		lcd.message('...file moved')
		sleep(5)
		lcd.clear()
		message = "NOTICE: File Transfer Success - " + filename + " --> " + location
		write_to_log(message)	
	else:
		if DEBUG:
			print "  " + filename + " not found or" 
			print "  " + location + " not accessible"
		lcd.clear()
		lcd.message('file not found\nor no permission')
		sleep(5)
		lcd.clear()
		message = "ERROR: File Transfer not sucessful - "   + filename + " --> " + location
		write_to_log(message)

def xsend(file):
	if DEBUG:
		print "==xsend function=="
		print "  send " + file + " to machine using rs232"
	if file_accessible(file,"r"):
		if DEBUG:
			print "  opening the file and converting to string"
		lcd.clear()
		lcd.message("converting...")
		fileHandle = open (file, 'r')
		data = fileHandle.read()
		fileHandle.close()
		if DEBUG:
			print "  file converted"
		lcd.clear()
		lcd.message("...file converted")
		sleep(1)

		#open serial object
		ser = create_serial()
		if DEBUG:
			print "  serial object created"
		lcd.clear()
		lcd.message("opening port..")
		ser.close()
		if DEBUG:
			print "  serial object closed"
		ser.open()
		if DEBUG:
			print "  serial object re-openend"

		#if the serial port is open, send the data string
		if DEBUG:
			print "  sending data..."
		lcd.clear()
		lcd.message("sending...")
		if ser.isOpen():                
			ser.write(data)
			if DEBUG:
				print "  data sent"
			ser.close()
			if DEBUG:
				print "  object closed"
		lcd.clear()
		lcd.message("data sent!")
		sleep(1)
		write_to_log("NOTICE: file successfully sent to machine")
		LcdGreen()

def xrec(file):
	
	if DEBUG:
		print "==xrec function=="
		print "  receive " + file + " from machine using rs232"
	try:
		rfile = open(file, 'w+')
		if DEBUG:
			print "  creating receiving file"
	except OSError:
		lcd.message("error w file")
		if DEBUG:
			print "  error creating file"
		return False

	
	ser = create_serial()
	if DEBUG:
		print " serial object created"
	lcd.clear()
	lcd.message("opening port")
	ser.close()
	if DEBUG:
		print "  serial object closed"
	ser.open()
	if DEBUG:
		print "  serial object re-openend"
		print "  receiving data..."
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
		print "  ...data received"
	ser.close()
	if DEBUG:
		print "  serial object closed"
	lcd.clear()
	lcd.message("data received")
	data = string.join(lines, "\n")
	if DEBUG:
		print " converting data array to string"
	lcd.clear()
	lcd.message("data converted")
	rfile.write(data)
	if DEBUG:
		print "  writing data to file"
	rfile.close()
	if DEBUG:
		print "  closing file"
	lcd.clear()
	lcd.message("data saved") 
	sleep(5)   

#===LCD FUNCTIONS===
# existing functions for controlling the LCD, Menu, and Buttons

def DoQuit():
	lcd.clear()
	lcd.message('Are you sure?\nPress Sel for Y')
	while 1:
		if lcd.buttonPressed(lcd.LEFT):
			break
		if lcd.buttonPressed(lcd.SELECT):
			lcd.clear()
			lcd.backlight(lcd.OFF)
			quit()
		sleep(0.25)

def DoShutdown():
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

def LcdOff():
	lcd.backlight(lcd.OFF)

def LcdOn():
	lcd.backlight(lcd.ON)

def LcdRed():
	lcd.backlight(lcd.RED)

def LcdGreen():
	lcd.backlight(lcd.GREEN)

def LcdBlue():
	lcd.backlight(lcd.BLUE)

def LcdYellow():
	lcd.backlight(lcd.YELLOW)

def LcdTeal():
	lcd.backlight(lcd.TEAL)

def LcdViolet():
	lcd.backlight(lcd.VIOLET)

def ShowDateTime():
	if DEBUG:
		print('in ShowDateTime')
	lcd.clear()
	while not(lcd.buttonPressed(lcd.LEFT)):
		sleep(0.25)
		lcd.home()
		lcd.message(strftime('%a %b %d %Y\n%I:%M:%S %p', localtime()))
	
def SetDateTime():
	if DEBUG:
		print('in SetDateTime')

def ShowIPAddress():
	if DEBUG:
		print('in ShowIPAddress')
	lcd.clear()
	lcd.message(commands.getoutput("/sbin/ifconfig").split("\n")[1].split()[1][5:])
	while 1:
		if lcd.buttonPressed(lcd.LEFT):
			break
		sleep(0.25)
	
class CommandToRun:
	def __init__(self, myName, theCommand):
		self.text = myName
		self.commandToRun = theCommand
	def Run(self):
		self.clist = split(commands.getoutput(self.commandToRun), '\n')
		if len(self.clist) > 0:
			lcd.clear()
			lcd.message(self.clist[0])
			for i in range(1, len(self.clist)):
				while 1:
					if lcd.buttonPressed(lcd.DOWN):
						break
					sleep(0.25)
				lcd.clear()
				lcd.message(self.clist[i-1]+'\n'+self.clist[i])          
				sleep(0.5)
		while 1:
			if lcd.buttonPressed(lcd.LEFT):
				break

class Widget:
	def __init__(self, myName, myFunction):
		self.text = myName
		self.function = myFunction
		
class Folder:
	def __init__(self, myName, myParent):
		self.text = myName
		self.items = []
		self.parent = myParent

def HandleSettings(node):
	global lcd
	if node.getAttribute('lcdColor').lower() == 'red':
		lcd.backlight(lcd.RED)
	elif node.getAttribute('lcdColor').lower() == 'green':
		lcd.backlight(lcd.GREEN)
	elif node.getAttribute('lcdColor').lower() == 'blue':
		lcd.backlight(lcd.BLUE)
	elif node.getAttribute('lcdColor').lower() == 'yellow':
		lcd.backlight(lcd.YELLOW)
	elif node.getAttribute('lcdColor').lower() == 'teal':
		lcd.backlight(lcd.TEAL)
	elif node.getAttribute('lcdColor').lower() == 'violet':
		lcd.backlight(lcd.VIOLET)
	elif node.getAttribute('lcdColor').lower() == 'white':
		lcd.backlight(lcd.ON)
	if node.getAttribute('lcdBacklight').lower() == 'on':
		lcd.backlight(lcd.ON)
	elif node.getAttribute('lcdBacklight').lower() == 'off':
		lcd.backlight(lcd.OFF)

def ProcessNode(currentNode, currentItem):
	children = currentNode.childNodes

	for child in children:
		if isinstance(child, xml.dom.minidom.Element):
			if child.tagName == 'settings':
				HandleSettings(child)
			elif child.tagName == 'folder':
				thisFolder = Folder(child.getAttribute('text'), currentItem)
				currentItem.items.append(thisFolder)
				ProcessNode(child, thisFolder)
			elif child.tagName == 'widget':
				thisWidget = Widget(child.getAttribute('text'), child.getAttribute('function'))
				currentItem.items.append(thisWidget)
			elif child.tagName == 'run':
				thisCommand = CommandToRun(child.getAttribute('text'), child.firstChild.data)
				currentItem.items.append(thisCommand)

class Display:
	def __init__(self, folder):
		self.curFolder = folder
		self.curTopItem = 0
		self.curSelectedItem = 0
	def display(self):
		if self.curTopItem > len(self.curFolder.items) - DISPLAY_ROWS:
			self.curTopItem = len(self.curFolder.items) - DISPLAY_ROWS
		if self.curTopItem < 0:
			self.curTopItem = 0
		if DEBUG:
			print('------------------')
		str = ''
		for row in range(self.curTopItem, self.curTopItem+DISPLAY_ROWS):
			if row > self.curTopItem:
				str += '\n'
			if row < len(self.curFolder.items):
				if row == self.curSelectedItem:
					cmd = '-'+self.curFolder.items[row].text
					if len(cmd) < 16:
						for row in range(len(cmd), 16):
							cmd += ' '
					if DEBUG:
						print('|'+cmd+'|')
					str += cmd
				else:
					cmd = ' '+self.curFolder.items[row].text
					if len(cmd) < 16:
						for row in range(len(cmd), 16):
							cmd += ' '
					if DEBUG:
						print('|'+cmd+'|')
					str += cmd
		if DEBUG:
			print('------------------')
		lcd.home()
		lcd.message(str)

	def update(self, command):
		if DEBUG:
			print('do',command)
		if command == 'u':
			self.up()
		elif command == 'd':
			self.down()
		elif command == 'r':
			self.right()
		elif command == 'l':
			self.left()
		elif command == 's':
			self.select()
	def up(self):
		if self.curSelectedItem == 0:
			return
		elif self.curSelectedItem > self.curTopItem:
			self.curSelectedItem -= 1
		else:
			self.curTopItem -= 1
			self.curSelectedItem -= 1
	def down(self):
		if self.curSelectedItem+1 == len(self.curFolder.items):
			return
		elif self.curSelectedItem < self.curTopItem+DISPLAY_ROWS-1:
			self.curSelectedItem += 1
		else:
			self.curTopItem += 1
			self.curSelectedItem += 1
	def left(self):
		if isinstance(self.curFolder.parent, Folder):
			# find the current in the parent
			itemno = 0
			index = 0
			for item in self.curFolder.parent.items:
				if self.curFolder == item:
					if DEBUG:
						print('foundit')
					index = itemno
				else:
					itemno += 1
			if index < len(self.curFolder.parent.items):
				self.curFolder = self.curFolder.parent
				self.curTopItem = index
				self.curSelectedItem = index
			else:
				self.curFolder = self.curFolder.parent
				self.curTopItem = 0
				self.curSelectedItem = 0
	def right(self):
		if isinstance(self.curFolder.items[self.curSelectedItem], Folder):
			self.curFolder = self.curFolder.items[self.curSelectedItem]
			self.curTopItem = 0
			self.curSelectedItem = 0
		elif isinstance(self.curFolder.items[self.curSelectedItem], Widget):
			if DEBUG:
				print('eval', self.curFolder.items[self.curSelectedItem].function)
			eval(self.curFolder.items[self.curSelectedItem].function+'()')
		elif isinstance(self.curFolder.items[self.curSelectedItem], CommandToRun):
			self.curFolder.items[self.curSelectedItem].Run()

	def select(self):
		if DEBUG:
			print('check widget')
		if isinstance(self.curFolder.items[self.curSelectedItem], Widget):
			if DEBUG:
				print('eval', self.curFolder.items[self.curSelectedItem].function)
			eval(self.curFolder.items[self.curSelectedItem].function+'()')

# now start things up
uiItems = Folder('root','')

dom = parse(configfile) # parse an XML file by name

top = dom.documentElement

ProcessNode(top, uiItems)

display = Display(uiItems)
display.display()

while 1:
	if (lcd.buttonPressed(lcd.LEFT)):
	   display.update('l')
	   display.display()

	if (lcd.buttonPressed(lcd.UP)):
		display.update('u')
		display.display()

	if (lcd.buttonPressed(lcd.DOWN)):
		display.update('d')
		display.display()

	if (lcd.buttonPressed(lcd.RIGHT)):
		display.update('r')
		display.display()

	if (lcd.buttonPressed(lcd.SELECT)):
		display.update('s')
		display.display()
	sleep(.25)
