#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
# Indigo Plugin for Candy House Sesame Locks
# Written by Travis Cook
# www.frightideas.com

import re
import time
import indigo
from datetime import datetime
import indigoPluginUtils
import pysesame




# Note the "indigo" module is automatically imported and made available inside
# our global name space by the host process.

################################################################################
class Plugin(indigo.PluginBase):

	########################################
	def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
		indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)

		self.mylogger = indigoPluginUtils.logger(self)

		self.States = self.enum(STARTUP=1, DELAY=2, IDLE=3)
		self.state = self.States.STARTUP
		self.logLevel = 1
		self.shutdownnow = False
		self.configRead = False
		self.sesames = []
		self.sesameList = []
		self.triggerList = []
		self.confirmList = {}
		self.candyAccount = None
		self.nextUpdateIn = 1000
		self.kAfterCommandDelay = 30
		self.kSesameUpdateDelay = 60


	def enum(self, **enums):
		return type('Enum', (), enums)

	def __del__(self):
		indigo.PluginBase.__del__(self)

	########################################
	def startup(self):
		self.mylogger.log(4, u"startup called")
		self.configRead = self.getConfiguration(self.pluginPrefs)

	def shutdown(self):
		self.mylogger.log(4, u"shutdown called")


	def updateSesameDeviceStates(self):

		for devid in self.sesameList:
			dev = indigo.devices[devid]
			s = None
			for sesame in self.sesames:
				if dev.pluginProps[u'sesameid'] == sesame.device_id: 
					s = sesame
					break

			if s is None:
				self.mylogger.logError("Indigo Sesame device '%s' not found in list from Candy House server." % dev.name)
				dev.setErrorStateOnServer('not found')
				return

			if dev.batteryLevel != s.battery:
				self.mylogger.log(1, u"Sesame lock '%s' battery level now '%d'" % (dev.name, s.battery))
				dev.updateStateOnServer(u"batteryLevel", value=s.battery)

			if dev.onState == True:
				if s.is_unlocked:
					self.mylogger.log(1, u"Sesame lock '%s' state is now Unlocked" % dev.name)					
					dev.updateStateOnServer(u"onOffState", False)
					dev.updateStateOnServer(u"lockstate", 'unlocked')
			else:
				if not s.is_unlocked:
					self.mylogger.log(1, u"Sesame lock '%s' state is now Locked" % dev.name)
					dev.updateStateOnServer(u"onOffState", True)
					dev.updateStateOnServer(u"lockstate", 'locked')					


	def getSesameById(self, id):
		for sesame in self.sesames:
			if sesame.device_id == id: 
				return sesame

		self.mylogger.logError("Sesame id '%s' not found in list from CandyHouse server." % id)
		return None


######################################################################################
	# Indigo Device Start/Stop
	######################################################################################

	def deviceStartComm(self, dev):
		self.mylogger.log(4, u"<<-- entering deviceStartComm: %s (%d - %s)" % (dev.name, dev.id, dev.deviceTypeId))

		props = dev.pluginProps

		if dev.deviceTypeId == u'sesame':
			if dev.id not in self.sesameList:
				self.sesameList.append(dev.id)
				if u'IsLockSubType' not in props:	
					props[u'IsLockSubType'] = True 				
					dev.replacePluginPropsOnServer(props)

				if len(self.sesames) > 0:
					self.updateSesameDeviceStates()

		self.mylogger.log(4, u"exiting deviceStartComm -->>")


	def deviceStopComm(self, dev):
		self.mylogger.log(4, u"<<-- entering deviceStopComm: %s (%d - %s)" % (dev.name, dev.id, dev.deviceTypeId))

		if dev.deviceTypeId == u'sesame':
			if dev.id in self.sesameList:
				self.sesameList.remove(dev.id)

		self.mylogger.log(4, u"exiting deviceStopComm -->>")

	######################################################################################
	# Indigo Trigger Start/Stop
	######################################################################################

	def triggerStartProcessing(self, trigger):
		self.mylogger.log(4, u"<<-- entering triggerStartProcessing: %s (%d)" % (trigger.name, trigger.id))
		self.triggerList.append(trigger.id)
		self.mylogger.log(4, u"exiting triggerStartProcessing -->>")

	def triggerStopProcessing(self, trigger):
		self.mylogger.log(4, u"<<-- entering triggerStopProcessing: %s (%d)" % (trigger.name, trigger.id))
		if trigger.id in self.triggerList:
			self.mylogger.log(4, u"TRIGGER FOUND")
			self.triggerList.remove(trigger.id)
		self.mylogger.log(4, u"exiting triggerStopProcessing -->>")

	#def triggerUpdated(self, origDev, newDev):
	#	self.mylogger.log(4, u"<<-- entering triggerUpdated: %s" % origDev.name)
	#	self.triggerStopProcessing(origDev)
	#	self.triggerStartProcessing(newDev)


	######################################################################################
	# Indigo Trigger Firing
	######################################################################################

	def triggerEvent(self, eventId):
		self.mylogger.log(4, u"<<-- entering triggerEvent: %s " % eventId)
		for trigId in self.triggerList:
			trigger = indigo.triggers[trigId]
			if trigger.pluginTypeId == eventId:
				indigo.trigger.execute(trigger)
		return


	######################################################################################
	# Indigo Action Methods
	######################################################################################
	#These are partition specific commands, except global and panic alarms.
	
	def actionControlDevice(self, action, dev):
		###### LOCK ######
		if action.deviceAction == indigo.kDeviceAction.Lock:
			# Command hardware module (dev) to LOCK here:
			sesame = self.getSesameById(dev.pluginProps[u'sesameid'])
			if sesame is None:
				return

			if sesame.lock() == True:
				indigo.server.log(u"Sesame server received lock command for '%s'.  We will confirm it actually locked shortly." % dev.name)
				dev.updateStateOnServer(u"onOffState", True)
				dev.updateStateOnServer(u"lockstate", 'locked')
				self.confirmList[dev.id] = True
				self.nextUpdateIn = self.kAfterCommandDelay
			else:
				indigo.server.log(u"send '%s' %s failed" % (dev.name, "lock"), isError=True)
			
	
		###### UNLOCK ######
		elif action.deviceAction == indigo.kDeviceAction.Unlock:
			# Command hardware module (dev) to turn UNLOCK here:
			sesame = self.getSesameById(dev.pluginProps[u'sesameid'])
			if sesame is None:
				return

			if sesame.unlock() == True:
				indigo.server.log(u"Sesame server received unlock command for '%s'.  We will confirm it actually unlocked shortly." % dev.name)
				dev.updateStateOnServer(u"onOffState", False)
				dev.updateStateOnServer(u"lockstate", 'unlocked')
				self.confirmList[dev.id] = False
				self.nextUpdateIn = self.kAfterCommandDelay			
			else:
				indigo.server.log(u"send '%s' %s failed" % (dev.name, "unlock"), isError=True)


		###### Request Status ######		
		elif action.deviceAction == indigo.kUniversalAction.RequestStatus:
			self.mylogger.log(1, u"Requesting status update of all Sesame Locks.")
			self.nextUpdateIn = 1




	######################################################################################
	# Indigo Pref UI Methods
	######################################################################################

	# Validate the pluginConfig window after user hits OK
	# Returns False on failure, True on success
	#
	def validatePrefsConfigUi(self, valuesDict):
		self.mylogger.log(3, u"validating Prefs called")
		errorMsgDict = indigo.Dict()
		wasError = False

		if len(valuesDict[u'email']) == 0:
			errorMsgDict[u'email'] = u"Please enter your Sesame account email address."
			wasError = True

		if len(valuesDict[u'email']) > 0:
			if not re.match(r"[^@]+@[^@]+\.[^@]+", valuesDict[u'email']):
				errorMsgDict[u'email'] = u"Please enter a valid email address."
				wasError = True

		if len(valuesDict[u'password']) == 0:
			errorMsgDict[u'password'] = u"Please enter your Sesame account password."
			wasError = True

		if wasError is True:
			return (False, valuesDict, errorMsgDict)

		# Tell plugin to reread it's config
		self.configRead = False

		# User choices look good, so return True (client will then close the dialog window).
		return (True, valuesDict)


	def validateDeviceConfigUi(self, valuesDict, typeId, devId):
		self.mylogger.log(3, u"validating Device Config called")
		self.mylogger.log(4, u"Type: %s, Id: %s, Dict: %s" % (typeId, devId, valuesDict))
		if typeId == u'sesame':
			id = valuesDict[u'sesameid']
			if len(id) == 0:
				errorMsgDict = indigo.Dict()
				errorMsgDict[u'sesameid'] = u"Please select a Sesame Lock from the list."
				return (False, valuesDict, errorMsgDict)

		return (True, valuesDict)


	def getSesameList(self, filter="", valuesDict=None, typeId="", targetId=0):	
		self.mylogger.log(3, u"getSesameList start")

		myArray = []

		if len(self.sesames) > 0:
			for sesame in self.sesames:
				self.mylogger.log(3, "Added: " + sesame.nickname)
				myArray.append((sesame.device_id, sesame.nickname))
		
		return myArray

	######################################################################################
	# Configuration Routines
	######################################################################################

	# Reads the plugins config file into our own variables
	#
	def getConfiguration(self, valuesDict):

		# Tell our logging class to reread the config for level changes
		self.mylogger.readConfig()

		self.mylogger.log(3, u"getConfiguration start")

		try:
			self.configEmail = valuesDict.get(u'email', '')
			self.configPass = valuesDict.get(u'password', '')

			self.mylogger.log(3, u"Configuration read successfully")

			return True

		except:
			self.mylogger.log(2, u"Error reading plugin configuration. (happens on very first launch)")

			return False


	######################################################################################
	# Communication Routines
	######################################################################################



	######################################################################################
	# Concurrent Thread
	######################################################################################

	def runConcurrentThread(self):
		self.mylogger.log(3, u"runConcurrentThread called")

		# While Indigo hasn't told us to shutdown
		while self.shutdownnow is False:

			self.nextUpdateIn -= 1

			if self.state == self.States.STARTUP:
				self.mylogger.log(3, u"STATE: Startup")

				if self.configRead is False:
					if self.getConfiguration(self.pluginPrefs) is True:
						self.configRead = True

				if self.configRead is True:
					self.mylogger.log(1, u'Logging into Candy House server.')
					self.candyAccount = pysesame.account()
					if self.candyAccount.login(self.configEmail, self.configPass) == True:
						self.sesames = pysesame.get_sesames(self.candyAccount)
						self.mylogger.log(1, u'Login succesful.  Found %d Sesame(s) in your account.' % len(self.sesames))
						for s in self.sesames:
							if s.api_enabled == False:
								self.mylogger.logError(u"Warning.  Sesame '%s' is not enabled for API access." % s.nickname)

						self.updateSesameDeviceStates()
						self.nextUpdateIn = self.kSesameUpdateDelay
						self.state = self.States.IDLE
					else:
						self.mylogger.logError(u'Login failed.  Will try again in 30 seconds.')
						self.nextUpdateIn = 30
						self.state = self.States.DELAY

			elif self.state == self.States.DELAY:
				self.mylogger.log(3, u"STATE: Delay")	
				if self.configRead is False:
					self.state = self.States.STARTUP			
				if self.nextUpdateIn <= 0:
					self.state = self.States.STARTUP

			elif self.state == self.States.IDLE:
				#self.mylogger.log(3, u"STATE: Idle")				
				if self.configRead is False:
					self.state = self.States.STARTUP
		
				if self.nextUpdateIn <= 0:
					self.sesames = pysesame.get_sesames(self.candyAccount)
					self.updateSesameDeviceStates()

					while len(self.confirmList) > 0:
						(devid, state) = self.confirmList.popitem()
						dev = indigo.devices[devid]
						if state != dev.onState:
							self.mylogger.logError(u"Sesame '%s' still hasn't changed to the requested state." % dev.name)
							self.triggerEvent(u'eventFailedToChange')
						else:
							self.mylogger.log(1, u"Sesame '%s' successfully changed state." % dev.name)

					self.nextUpdateIn = self.kSesameUpdateDelay

			# loop delay
			self.sleep(1)

		self.mylogger.log(3, u"Exiting Concurrent Thread")


	def stopConcurrentThread(self):
		self.mylogger.log(3, u"stopConcurrentThread called")
		self.shutdownnow = True
		self.mylogger.log(3, u"Exiting stopConcurrentThread")
