# AppDaemon Watchman

The world around us is constantly changing and so is Home Assistant. How often have you found yourself in a situation when your automations had stopped working because some entities become permanently unavailable or service changed their name? For example, Home Assistant companion app can easily change the name of its services and sensors it exposes to Home Assistant after you change the device name in the configuration. The watchman is an attempt to control such changes and make you able to react proactively before some critical automation will break.

## What does it do
The app attempts to collect all the Home Assistant entities (sensors, timers, input_selects, and so on) mentioned in your yaml configuration files as well as all the services. Having a list of all entities, the app checks their state one by one and reports those not available or missing. For services, the app checks whether service is available in the service registry and reports missing services via notification service of choice (unless it is missing too :). The [example of a report](https://github.com/dummylabs/watchman#example-of-watchman-report) is given below.

### Disclaimer and some internal details
The app has very simple internals, it knows nothing about complex relationships and dependencies among yaml configuration files as well as nothing about the semantics of entities and automations. It parses yaml files line by line in the given folders and tries to guess references either to an entity or to a service based on regexp rules. That means it can give both false positives (something which looks like a duck, swims like a duck, and quacks like a duck, but is not) and false negatives (when some entity in a configuration file was not detected by the app). To reduce false positives ignore list can be used for the entities/services and for configuration folders exclusion list is used (see Configuration section below). Improvements for false negatives are a goal for future releases. 

# Installation

## AppDaemon installation 

You will need to have AppDaemon installed to run watchman. If you use Home Assistant Operating System or Home Assistant Supervised, the easiest way to install AppDaemon 4 will be the addon from the Add-on store. Once the addon is installed and started it will create a folder in /config/appdaemon with the needed structure for AppDaemon to run. AppDaemon can also be installed for HA Container and HA Core flavors, check the documentation here: https://appdaemon.readthedocs.io/en/latest/INSTALL.html 

## Watchman installation 
Once you have AppDaemon up and running (check the logs), you can proceed to install watchman either manually or through HACS. It is important to have AppDaemon up and running before installing watchman.

### Install with HACS 
This is a recommended way to install watchman. Installation in HACS is done in three simple steps:
1. Make sure "Enable AppDaemon apps discovery & tracking" option is active. It's located in Configuration -> Devices & Services -> HACS -> Configure. 
2. Go to the "Automation" section on HACS, tap the three-dots menu in the upper right corner, go to "Custom repositories". Add new repository `dummylabs/watchman` with AppDaemon category. If Custom Repositories is hidden, wait until background task of HACS finished and custom repositories are unblocked. 
3. Click the big blue button "Explore and download repositories" and search for "watchman", then click "Download this repository with HACS". 

#### Check if watchman is up and running

Go to Configuration->Addons, Backups & Supervisor -> AppDaemon 4 -> Log. If watchman is installed, you should find following line in AppDaemon log: `INFO AppDaemon: Initializing app watchman using class Watchman from module watchman`.

When the application is installed, check its configuration file in `/config/appdaemon/apps/watchman/watchman.yaml` and adjust it according to information from section Configuration below.

### Manual install
Download the latest version of watchman.py and watchman.yaml, and then copy them to `/config/appdaemon/apps/watchman`. The files need to be in `/config/appdaemon/apps/watchman/watchman.py` and `/config/appdaemon/apps/watchman/watchman.yaml` respectively. 


## Configuration

Configuration file is located in `/config/appdaemon/apps/watchman/watchman.yaml`


Options:
---

Key | Required | Description | Default 
------------ | ------------- | ------------- | ------------- 
module | True | Appdaemon requirement | `"watchman"`
class | True | Appdaemon requirement | `"Watchman"` 
globals | True | Appdaemon requirement | `"utils"`
notify_service | False | Home assistant notification service to sent report via | `None` 
included_folders | False | List of folders to scan for entities and services recursively | `"/config"`
excluded_folders | False | List of folders to exclude from the scan. Takes precedence over included_folders | `None`
report_header | False | Custom header for watchman report | `"=== Watchman Report ==="`
ignored_items | False | List of items to ignore. The entity/service will be excluded from the report if their name fully matches one from the ignore list | `None`
ignored_states | False | List of entity states which should be ignored. Possible items are: missing, unavailable, unknown | `None`
chunk_size | False | Average size of a notification message in bytes. If report text size exceeds chunk_size, the report will be sent in several subsequent messages. | `3500`

### Minimal working example apps.yaml:

```
watchman:
  module: watchman
  class: Watchman
  notify_service: notify.telegram

global_modules: utils
```

### Advanced configuration

TODO

## Usage

The audit can be triggered by firing event `ad.watchman_audit` from automation or a script. Once the event is fired, the report will be prepared and saved to `/config/watchman_report.txt`. If configuration parameter `notify_service` is set, the report will allso be sent as a notification. A long report may be split into several messages due to limitations imposed by notification services (e.g. telegram). 
The event handler will create a text file with the report and will try to send a notification via default notification service. This behavior can be altered with two additional parameters in the event data:

 - create_file: True 
 - send_notification: True 

If one or both pafameters were not set, they are `True` by default. 

Automation example:

```
event: ad.watchman.audit
event_data:
  create_file: true
  send_notification: false
```

Besides of report, a few sensors will be automatically created or updated:

- sensor.watchman_missing_entities
- sensor.watchman_missing services

Please note that, due to the nature of AppDaemon created entities, these sensors are not persistent and will not be available after Home Assistant reboot until event.watchman_audit is fired again.

## Example of a watchman report
```
=== Watchman Report === 

=== Missing 2 service(-s) from 39 found in your config:
tts.yandextts_say in {'/config/automations.yaml': [100]}
notify.mobile_app_vog_l29 in {'/config/scripts.yaml': [65]}

=== Missing 51 entity(-es) from 239 found in your config:
sensor.pm25_mean[unavailable] in: {'/config/customize.yaml': [6]}
sensor.stats_pm25_10_median[unavailable] in: {'/config/customize.yaml': [17]}
automation.notify_low_battery_huawei[missing] in: {'/config/automations.yaml': [17, 28]}
automation.notify_mobile_call[missing] in: {'/config/automations.yaml': [20, 31]}
binary_sensor.macbook_pro_active[missing] in: {'/config/automations.yaml': [79, 115, 120, 139]}
timer.finished[missing] in: {'/config/automations.yaml': [178, 240, 1466]}
sensor.xiaomi_miio_sensor[unavailable] in: {'/config/automations.yaml': [204, 263, 1386]}
sensor.huawei_p30_pro_sostoianie_telefona[missing] in: {'/config/automations.yaml': [453]}
automation.system_automation_error[missing] in: {'/config/automations.yaml': [911]}
group.battery_devices[unknown] in: {'/config/automations.yaml': [1018]}
sensor.scrape_ikea_tradfri_100lm[missing] in: {'/config/automations.yaml': [1125]}
media_player.lgtv[missing] in: {'/config/automations.yaml': [1266, 1272]}
light.bedlight_bedroom[missing] in: {'/config/scenes.yaml': [4]}
group.calendar[missing] in: {'/config/google_calendars.yaml': [9, 30, 37]}
group.v[missing] in: {'/config/google_calendars.yaml': [16, 23]}
calendar.google[missing] in: {'/config/google_calendars.yaml': [16, 23]}
sensor.xiaomi_miio_pm25sensor[missing] in: {'/config/entities/binary_sensors/pm25_rising.yaml': [4]}
sensor.z2m_button_2_battery[missing] in: {'/config/entities/groups/monitored_entities.yaml': [10]}
sensor.z2m_temp_egor_battery[unavailable] in: {'/config/entities/groups/monitored_entities.yaml': [21]}
device_tracker.egor_phone[missing] in: {'/config/entities/persons/egor.yaml': [5]}
sensor.pm25_mean_100[unavailable] in: {'/config/entities/sensors/stats_pm25_100_median.yaml': [4]}
sensor.xiaomi_miio_pm25sensor_f[missing] in: {'/config/entities/sensors/stats_pm25.yaml': [2]}
sensor.tion_breezer_pm25_force_update2[unavailable] in: {'/config/entities/sensors/stats_pm25.yaml': [3]}
sensor.pm25_mean_15[unavailable] in: {'/config/entities/sensors/stats_pm25_15_median.yaml': [4]}
fan.zhimi_humidifier_ca1[unavailable] in: {'/config/entities/sensors/zhimi_humidifier_waterlevel.yaml': [6, 8, 9]}
sensor.pm25_mean_20[unavailable] in: {'/config/entities/sensors/stats_pm25_20_median.yaml': [4]}
sensor.pm25_mean_50[unavailable] in: {'/config/entities/sensors/stats_pm25_50_median.yaml': [4]}
zone.work[missing] in: {'/config/entities/sensors/yandex_maps_work.yaml': [3]}
sensor.pm25_mean_5[unavailable] in: {'/config/entities/sensors/stats_pm25_5_median.yaml': [4]}
sensor.senseair2_co2_value[missing] in: {'/config/lovelace/views/mobile.yaml': [37]}
weather.gismeteo_daily[missing] in: {'/config/lovelace/views/weather.yaml': [10]}
binary_sensor.coffee_maker_last_changed[missing] in: {'/config/lovelace/views/floorplan.yaml': [9]}
sensor.humidifier_water_level[unknown] in: {'/config/lovelace/views/floorplan.yaml': [119]}
sensor.z2m_temp_egor_temperature[unavailable] in: {'/config/lovelace/views/floorplan.yaml': [154]}
sensor.z2m_temp_egor_humidity[unavailable] in: {'/config/lovelace/views/floorplan.yaml': [161]}
sensor.senseair_co2_value[missing] in: {'/config/lovelace/views/floorplan.yaml': [285]}
sensor.temperature_kitchen[unavailable] in: {'/config/lovelace/views/floorplan.yaml': [294]}
sensor.humidity_kitchen[unavailable] in: {'/config/lovelace/views/floorplan.yaml': [301]}
binary_sensor.masha_room[missing] in: {'/config/integrations/logbook.yaml': [12]}
media_player.shield[unavailable] in: {'/config/integrations/logbook.yaml': [27]}
sensor.ups_status_date[missing] in: {'/config/integrations/recorder.yaml': [13]}
sensor.temperature_egor[missing] in: {'/config/integrations/influxdb.yaml': [9]}
sensor.gismeteo_temperature[missing] in: {'/config/integrations/influxdb.yaml': [11]}
sensor.temperature_masha[missing] in: {'/config/integrations/influxdb.yaml': [12]}
sensor.yandex_weather_temperature[missing] in: {'/config/integrations/influxdb.yaml': [13]}
sensor.pressure_egor[missing] in: {'/config/integrations/influxdb.yaml': [19]}
sensor.pressure_kitchen[unavailable] in: {'/config/integrations/influxdb.yaml': [20]}
sensor.pressure_masha[missing] in: {'/config/integrations/influxdb.yaml': [21]}
media_player.yandex_intents[unknown] in: {'/config/integrations/yandex_smart_home.yaml': [11]}
sensor.apm25_10_median_stats[missing] in: {'/config/customizations/entities/sensor.pm25_10_median_stats.yaml': [1]}
person.egor[unknown] in: {'/config/customizations/entities/person.egor.yaml': [1]}

=== Parsed 213 yaml files in 0.31 s.
```
