#encoding: utf-8
import appdaemon.plugins.hass.hassapi as hass
from datetime import datetime
import utils
import re
import os
import yaml
import time

APP_NAME = "watchman"
APP_CFG_PATH = "/config/appdaemon/apps/watchman/watchman.yaml"
EVENT_NAME = "ad.watchman.audit"
APP_FOLDER = "/config/appdaemon/apps/watchman"

class Watchman(hass.Hass):
    def initialize(self):
        self.included_folders = self.args.get('included_folders', ['/config'])

        if not isinstance(self.included_folders, list) or len(self.included_folders) == 0:
            self.persistent_notification(f"invalid {APP_NAME} config", 
            f"`included_folders` parameter in `{APP_CFG_PATH}` should be "
            "a list with at least 1 folder in it", error=True)
        self.excluded_folders =  self.args.get('excluded_folders', [])

        if not isinstance(self.excluded_folders, list):
            self.persistent_notification(f"invalid {APP_NAME} config", 
            f"`excluded_folders` parameter in `{APP_CFG_PATH}` should be "
            "a list not single value", error=True)
        self.report_header = self.args.get('report_header', '=== Watchman Report ===')

        # large reports are divided into chunks (size in bytes) as notification services
        # may reject very long messages
        self.chunk_size = self.args.get('chunk_size', 3500)
        self.notify_service = self.args.get('notify_service', None)

        self.ignore = self.args.get('ignored_items', [])
        if not isinstance(self.ignore, list):
            self.persistent_notification(f"invalid {APP_NAME} config", 
            f"`ignored_items` parameter in `{APP_CFG_PATH}` should be a list", 
            error=True)

        self.ignored_states = self.args.get('ignored_states', [])
        if not isinstance(self.ignored_states, list):
            self.persistent_notification(f"invalid {APP_NAME} config", 
            f"`ignored_states` parameter in `{APP_CFG_PATH}` should be a list", error=True)

        self.report_path = self.args.get('report_path', '/config/watchman_report.txt')

        folder, _ = os.path.split(self.report_path)
        if not os.path.exists(folder):
            self.persistent_notification("Error from watchman", 
            f"Incorrect `report_path` {self.report_path}.", error=True)

        if not self.get_flag('.skip_greetings'):
            self.set_flag('.skip_greetings')
            self.persistent_notification("Hello from watchman!", 
            "Congratulations, watchman is up and running!\n\n "
            f"Please adjust `{APP_CFG_PATH}` config file according "
            "to your needs or just go to Developer Tools->Events "
            f"and fire up `{EVENT_NAME}` event.")

        self.listen_event(self.on_event, event=EVENT_NAME)
        #self.audit(ignored_states = self.ignored_states)

    def persistent_notification(self, title, msg, error=False):
        self.call_service("persistent_notification/create", title = title, message = msg )
        if error:
            raise Exception(msg)

    def on_event(self, event_name, data, kwargs):
        create_file = data.get("create_file", True)
        send_notification = data.get("send_notification", True)
        self.audit(create_report_file = create_file, notification = send_notification, ignored_states = self.ignored_states)

    def load_services(self):
        services = []
        service_data = self.list_services(namespace="global")
        for s in service_data:
            services.append(f"{s['domain']}.{s['service']}")
        return services

    def audit(self, create_report_file, notification, ignored_states = []):
        start_time = time.time()
        entity_list, service_list, files_parsed = utils.parse(self.included_folders, 
        self.excluded_folders, self)
        self.log(f"Found {len(entity_list)} entities, {len(service_list)} services ")
        if files_parsed == 0:
            self.log('No yaml files found, please check apps.yaml config', level="ERROR")
            self.report('No automation files found, please check apps.yaml config')
            return

        entities_missing = {}
        services_missing = {}
        for entity, occurences in entity_list.items():
            state = self.get_state(entity) or 'missing'
            if entity in self.ignore or state in ignored_states:
                continue            
            if state in ['missing', 'unknown', 'unavailable']:
                entities_missing [entity] = occurences

        service_registry = self.load_services()
        for service, occurences in service_list.items():
            if service not in service_registry and service not in self.ignore:
                services_missing[service] = occurences

        self.set_state("sensor.watchman_missing_entities", state=len(entities_missing))
        self.set_state("sensor.watchman_missing_services", state=len(services_missing))

        report_chunks = []
        chunk_size = 3500

        report = "" 
        report += f"{self.report_header} \n"

        if services_missing:
            report += f"\n=== Missing {len(services_missing)} service(-s) from {len(service_list)} found in your config:\n"
            for service in services_missing: 
                report += f"{service} in {service_list[service]}\n"
                if len(report) > self.chunk_size:
                    report_chunks.append(report)
                    report = ""
        elif len(service_list) > 0:
            report += f"\n=== Congratulations, all {len(service_list)} services from your config are available!\n"
        else:
            report += f"\n=== No services found in configuration files!\n"

        if entities_missing:
            report += f"\n=== Missing {len(entities_missing)} entity(-es) from {len(entity_list)} found in your config:\n"
            for entity in entities_missing:
                state = self.get_state(entity) or 'missing'
                report += f"{entity}[{state}] in: {entity_list[entity]}\n"
                if len(report) > self.chunk_size:
                    report_chunks.append(report)
                    report = ""
        elif len(entity_list) > 0:
            report += f"\n=== Congratulatiions, all {len(entity_list)} entities from your config are available!"
        else:
            report += f"\n=== No entities found in configuration files!\n"

        report += f"\n=== Parsed {files_parsed} yaml files in {(time.time()-start_time):.2f} s."
        report_chunks.append(report)

        if create_report_file:
            if not self.get_flag('.skip_achievement'):
                self.set_flag('.skip_achievement')
                self.persistent_notification("Achievement unlocked: first report!", 
                f"Your first report was stored in `{self.report_path}` \n\n " 
                "TIP: set `notify_service` parameter in configuration file to "
                "receive report via notification service of choice. \n\n "
                "This is one-time message, it will not bother you in the future.")

            report_file = open(self.report_path, "w")
            for chunk in report_chunks:
                report_file.write(chunk)
            report_file.close()
        if notification:
            if (entities_missing or services_missing):
                self.send_notification(report_chunks)
            else:
                self.log("Entities and services are fine, no notification required")

    def send_notification(self, report):
        if not self.notify_service in self.load_services():
            self.persistent_notification(f"invalid {APP_NAME} config", 
            f"{self.notify_service} service was not found in service registry. "
            f"Please specify a valid notification service, e.g. `notify.telegram`", error=True)
        elif not self.notify_service:
            self.persistent_notification(f"invalid {APP_NAME} config", 
            f"Set `notify_service` parameter in `{APP_CFG_PATH}`, to a notification "
            "service, e.g. `notify.telegram`", error=True)            
        for chunk in report:
            self.call_service(self.notify_service.replace('.','/'), message=chunk)

    def set_flag(self, flag):
        report_file = open(os.path.join(APP_FOLDER, flag), "w")
        report_file.close()

    def get_flag(self, flag):
        return os.path.exists(os.path.join(APP_FOLDER, flag))

