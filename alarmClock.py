#mix of imports from the server.py and alarm clock
import sys
import RPi.GPIO as GPIO
import time
import thread

from datetime import date, datetime
from twisted.internet import defer
from twisted.internet.protocol import DatagramProtocol
from twisted.internet import reactor
from twisted.python import log
from gpiozero import Buzzer, Button

import txthings.resource as resource
import txthings.coap as coap

ALARM_TIME = ""

#gpiozero buzzer and button setup
BUZZER = Buzzer(17)
BUTTON = Button(20)
ON = True

#took resource skeleton code from project 2 and sets GET and PUT commands
#which give an inputted time to global variable ALARM_TIME for later
class AlarmResource (resource.CoAPResource):

    def __init__(self):
        resource.CoAPResource.__init__(self)
        self.visible = True

    def render_GET(self, request):
        payload=" input time in this order: HH:MM PM/AM"
        response = coap.Message(code=coap.CONTENT, payload=payload)
        return defer.succeed(response)

    def render_PUT(self, request):
        log.msg('PUT payload: %s', request.payload)
        global ALARM_TIME
        ALARM_TIME = request.payload
        payload = "time recieved"
        response = coap.Message(code=coap.CHANGED, payload=payload)
        return defer.succeed(response)

#kept this from project 2 since its used to discover resources
class CoreResource(resource.CoAPResource):

    def __init__(self, root):
        resource.CoAPResource.__init__(self)
        self.root = root

    def render_GET(self, request):
        data = []
        self.root.generateResourceList(data, "")
        payload = ",".join(data)
        log.msg("%s", payload)
        response = coap.Message(code=coap.CONTENT, payload=payload)
        response.opt.content_format = coap.media_types_rev['application/link-format']
        return defer.succeed(response)

#allows button to be used as off switch for alarm        
def Off_Switch():
    global ON
    ON = not ON
BUTTON.when_pressed = Off_Switch

#defines the clock thread that will run along side the server
def run_clock(name):
	while True:
		#takes datetime of current time
		today = datetime.today()
		
		#formats date into day, month, year, and localizes time into AM/PM
		dateString = today.strftime("%a %b %d, %Y")
		timeString = today.strftime("%I:%M %p")
		
		lcd_text(dateString, LCD_LINE_1)
		lcd_text(timeString, LCD_LINE_2)
		stringTime = dateString + " " + timeString
		time.sleep(3)
		
		#sends different text to LCD depending on if ALARM_TIME is set
		if ALARM_TIME == "":
			lcd_text("No alarm set", LCD_LINE_1)
			lcd_text("Wait for input", LCD_LINE_2)
		else:
			lcd_text("Alarm Set To", LCD_LINE_1)
			lcd_text("", LCD_LINE_2)
			time.sleep(1)
			lcd_text(ALARM_TIME, LCD_LINE_1)
		time.sleep(3)
		
		#checks for the ON switch and time and will run until ON = False
		while ALARM_TIME == timeString and ON == True:
			lcd_text("ALARM GOING", LCD_LINE_1)
			lcd_text("PRESS BUTTON", LCD_LINE_2)
			BUZZER.on()
			time.sleep(1)
			BUZZER.off()
			time.sleep(1)
			BUZZER.on()
			time.sleep(1)
			BUZZER.off()

#intialization of LCD display with memory bits
#this code was taken from a LCD tutorial linked below
#https://www.mbtechworks.com/projects/drive-an-lcd-16x2-display-with-raspberry-pi.html
def lcd_init():
	lcd_write(0x33, LCD_CMD)
	lcd_write(0x32, LCD_CMD)
	lcd_write(0x06, LCD_CMD)
	lcd_write(0x0C, LCD_CMD)
	lcd_write(0x28, LCD_CMD)
	lcd_write(0x01, LCD_CMD)
	time.sleep(0.0005)
	
def lcd_write(bits, mode):
	GPIO.output(LCD_RS, mode)
	GPIO.output(LCD_D4, False)
	GPIO.output(LCD_D5, False)
	GPIO.output(LCD_D6, False)
	GPIO.output(LCD_D7, False)
	if bits & 0x10 == 0x10:
		GPIO.output(LCD_D4, True)
	if bits & 0x20 == 0x20:
		GPIO.output(LCD_D5, True)
	if bits & 0x40 == 0x40:
		GPIO.output(LCD_D6, True)
	if bits & 0x80 == 0x80:
		GPIO.output(LCD_D7, True)

	lcd_toggle_enable()
	
	GPIO.output(LCD_D4, False)
	GPIO.output(LCD_D5, False)
	GPIO.output(LCD_D6, False)
	GPIO.output(LCD_D7, False)
	if bits & 0x01 == 0x01:
		GPIO.output(LCD_D4, True)
	if bits & 0x02 == 0x02:
		GPIO.output(LCD_D5, True)
	if bits & 0x04 == 0x04:
		GPIO.output(LCD_D6, True)
	if bits & 0x08 == 0x08:
		GPIO.output(LCD_D7, True)
		
	lcd_toggle_enable()

def lcd_toggle_enable():
	time.sleep(0.0005)
	GPIO.output(LCD_E, True)
	time.sleep(0.0005)
	GPIO.output(LCD_E, False)
	time.sleep(0.0005)
	
def lcd_text(message, line):
	message = message.ljust(LCD_CHARS, " ")
	lcd_write(line, LCD_CMD)
	for i in range(LCD_CHARS):
		lcd_write(ord(message[i]), LCD_CHR)

LCD_RS = 7
LCD_E = 8
LCD_D4 = 25
LCD_D5 = 24
LCD_D6 = 23
LCD_D7 = 18

LCD_CHR = True
LCD_CMD = False
LCD_CHARS = 16
LCD_LINE_1 = 0x80
LCD_LINE_2 = 0xC0

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(LCD_E, GPIO.OUT)
GPIO.setup(LCD_RS, GPIO.OUT)
GPIO.setup(LCD_D4, GPIO.OUT)
GPIO.setup(LCD_D5, GPIO.OUT)
GPIO.setup(LCD_D6, GPIO.OUT)
GPIO.setup(LCD_D7, GPIO.OUT)

lcd_init()

#start of before the server since server takes priority of main program thread
thread.start_new_thread(run_clock, ("clock_thread",))

#server startup
log.startLogging(sys.stdout)
root = resource.CoAPResource()
	
well_known = resource.CoAPResource()
root.putChild('.well-known', well_known)
	
core = CoreResource(root)
well_known.putChild('core', core)
	
alarm = AlarmResource()
root.putChild('alarm', alarm)
endpoint = resource.Endpoint(root)
reactor.listenUDP(coap.COAP_PORT, coap.Coap(endpoint)) #, interface="::")
reactor.run()
