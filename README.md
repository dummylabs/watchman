# AppDaemon watchman

The world around us is constantly changing and so is Home Assistant. How many times you found yourself in situation when your automations had stopped to work because some entities become permanently unavailable or a service changed its name? For me this is especially true with Home Asisstant companion app which can easily change the name of the services it provides and sensors it exposes to Home Assistant with small changes to its configuration. The watchman is an attempt to control those changes and make you able to react proactively before some critical automation will break.

## What does it do
The app attempts to collect all the entities (sensors, timers, input_selects and so on) mentioned in your yaml configuration files as well as all the services. Having a list of all entities, it checks their state one by one and reports those not available or missing. For services, the app checks whether service is available in service registry and reports missing services via notification service of choice (unless it is missing too :). 

### Disclaimer and some internal details
The app has very simple internals, it knows nothing about complex relationships and dependencies among yaml configuration files as well as nothing about semanthics of entities and automations. It parses yaml files line by line in the given folders and tries to guess references either to an entity or to a service based on regexp rules. That means it can give both false positives (something which looks like a duck, swims like a duck, and quacks like a duck, but is not) and false negatives (when some entity was not detected by the app). In order to reduce false positives ignore list can be used for the entities/services and for configuration folders exclusion list is used (see Configuration section below). Improvements for false negatives are a goal for the future releases. 

# Installation

## AppDaemon installation 

You will need to have AppDaemon installed in order to run watchman. If you use Home Assistant Operating System or Home Assistant Supervised, the easiest way to install AppDaemon 4 will be addon from the Add-on store. Once the addon is installed it will create a folder in /config/appdaemon with the needed structure for AppDaemon to run. AppDaemon can also be installed for HA Container and HA Core flavours, check the documentation here: https://appdaemon.readthedocs.io/en/latest/INSTALL.html 

## watchman installation 
Once you have AppDaemon up and running (check the logs), you can proceed to install watchman either manually or through HACS. It is important to have AppDaemon up and running before installing watchman.

### HACS 
This is a recommended way to install watchman. Installation in HACS is done in three simple steps:
1. make sure "Enable AppDaemon apps discovery & tracking" option is active. It's located in Configuration -> Devices & Services -> HACS -> Configure. 
2. go to the "Automation" section on HACS, tap tree dots menu in the upper right corner, go to "Custom repositories". Add new repository dummylabs/watchman with AppDaemon category.
3. click the big blue button "Explore and download repositories" and search for watchman, then click "Download this repository with HACS". 

When application is installed, check its configuration file in /config/appdaemon/apps/watchman/watchman.yaml and adjust it according to information from section Configuration below.

### Manual 
Download the latest version of watchman.py and watchman.yaml, and then place the watchman folder in your /config/appdaemon/apps/watchman. The files need to be in /config/appdaemon/apps/watchman/watchman.py and /config/appdaemon/apps/watchman/watchman.yaml respectively. 

## Configuration

## Usage

The audit can be triggered by firing event.watchman_audit from an automation or a script. Once the event fired, the report will be sent using default notification service from the app configuration. On top of that a few sensors will be automatically updated:

- sensor.watchman_total_entities
- sensor.watchman_missing_entities
- sensor.watchman_total_services
- sensor.watchman_missing services

Please note that, due to the nature of AppDaemon created entities, these sensors are not persistent and will not be available after Home Assistant reboot until event.watchman_audit is fired again.
