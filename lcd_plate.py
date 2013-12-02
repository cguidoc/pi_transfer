#!/usr/bin/python

from time import sleep
from Adafruit_CharLCDPlate import Adafruit_CharLCDPlate
import xserial


# Initialize the LCD plate.  Should auto-detect correct I2C bus.  If not,
# pass '0' for early 256 MB Model B boards or '1' for all later versions
global lcd = Adafruit_CharLCDPlate()

# Clear display and show greeting, pause 1 sec
lcd.clear()
lcd.message("EBE wifi <--> RS232 bridge\nv0.1")
sleep(1)
lcd.clear()

# Cycle through backlight colors
col = (lcd.RED , lcd.YELLOW, lcd.GREEN, lcd.TEAL,
       lcd.BLUE, lcd.VIOLET, lcd.ON   , lcd.OFF)
for c in col:
    lcd.backlight(c)
    sleep(.5)

lcd.backlight(lcd.BLUE)

# Poll buttons, display message & set backlight accordingly
btn = ((lcd.LEFT  , 'Red Red Wine'              , lcd.RED),
       (lcd.UP    , 'Sita sings\nthe blues'     , lcd.BLUE),
       (lcd.DOWN  , 'I see fields\nof green'    , lcd.GREEN),
       (lcd.RIGHT , 'Purple mountain\nmajesties', lcd.VIOLET),
       (lcd.SELECT, ''                          , lcd.ON))
prev = -1

if __name__ == '__main__':
  lcd.message("Checking for files...")
  sleep(1)
  lcd.clear()
  while xserial.file_accessible("transfer.txt", "r"):
    lcd.message("transfer.txt found \npress select to transfer")
    lcd.backlight(lcd.GREEN)
    if lcd.buttonPressed(0):
      lcd.backlight(lcd.YELLOW)
      xserial.serial_xfer("transfer.txt")
      sleep(1)
      lcd.backlight(lcd.BLUE)
      lcd.message("transfer comp")
