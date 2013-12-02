#!/usr/bin/python
'''Transfter file to serial port

This takes a file, converts it to a string and send it to 
the serial port'''

__author__ 		= "Chris Guidotti"
__version__ 	= "$Revision: 0.1 $"
__date__ 		= "$Date: 2013/11/20 $"


import serial
from time import sleep

def file_accessible(filepath, mode):
  '''check if a file exists and is accessable'''
  try:
    f = open(filepath, mode)
  except IOError as e:
  	return False

  return True

def serial_xfer(file):
	'''Takes a file as input and sends the data in the file to the serial port'''
	global lcd

	if file_accessible(file,"r"):
		#open the file and convert to string
		print "opening the file and converting to string"
		#lcd.message("converting")
		fileHandle = open (file, 'r')
		data = fileHandle.read()
		fileHandle.close()
		print data
		print "file converted"
		#lcd.clear()
		#lcd.message("file converted")
		sleep(1)

		#open serial object
		print "opening serial port object"
		#lcd.clear()
		#lcd.message("opening port")
		ser = serial.Serial(port = "/dev/ttyUSB0", baudrate=9600)
		print "  object created"
		ser.close()
		print "  object closed"
		ser.open()
		print "  object re-openend"

		#if the serial port is open, send the data string
		print "sending data..."
		#lcd.clear()
		#lcd.message("sending...")
		if ser.isOpen(): 	  			
			ser.write(data)
			print "...data sent"
			sleep(1)

if __name__ == '__main__':
	serial_xfer(test.txt)
	
