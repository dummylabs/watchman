# AppDaemon watchman

The world around us is constantly changing and so is Home Assistant. How many times you found yourself in situation when your automations had stopped to work because some entities become permanently unavailable or a service changed its name? For example, Home Asisstant companion app can easily change the name of its services and sensors it exposes to Home Assistant after you change device name in configuration. The watchman is an attempt to control such changes and make you able to react proactively before some critical automation will break.

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

### Minimal working example apps.yaml:

Options:
---

Key | Required | Description | Default 
------------ | ------------- | ------------- | ------------- 
module | True | Appdaemon requirement | "watchman"
class | True | Appdaemon requirement | "Watchman" 
globals | True | Appdaemon requirement | "utils"
notify_service | False | Home assistant notiication service to sent report via | None 
included_folders | False | List of folders to scan for entities and services | "/config"
excluded_folders | False | List of folders to exclude from scan. Takes precedence over included_folders | None
report_header | False | Custom header for watchman report | "=== Watchman Report ==="
ignored_items | False | List of items to ignore. The entity/service will be excluded from the report if their name fully matches one from the ignore list | None
ignored_states | False | List of entity states which should be ignored. Possible items are: missing, unavailable, unknown | None
chunk_size | False | Average size of a notification message in bytes. If report text size exceeds chunk_size, the report will be sent in several subsequent messages. | 3500


```
watchman:
  module: watchman
  class: Watchman
  notify_service: notify.telegram

global_modules: utils
```

## Usage

The audit can be triggered by firing event ad.watchman_audit from an automation or a script. Once the event fired, the report will be prepared and saved to /config/watchman_report.txt. If configuration parameter notify_service is set, the report will be sent as a notification. Long report may be splitted in several messages due to limitations imposed by notification services (e.g. telegram). Besides of report, a few sensors will be automatically created or updated:

- sensor.watchman_missing_entities
- sensor.watchman_missing services

Please note that, due to the nature of AppDaemon created entities, these sensors are not persistent and will not be available after Home Assistant reboot until event.watchman_audit is fired again.
