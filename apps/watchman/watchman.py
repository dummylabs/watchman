#encoding: utf-8
import appdaemon.plugins.hass.hassapi as hass
from datetime import datetime
import utils
import re
import os
import yaml
import time

APP_NAME = "watchman"
APP_CFG_PATH = "/config/appdaemon/watchman/watchman.yaml"

class Watchman(hass.Hass):
    def initialize(self):
        self.entity_pattern = entity_pattern = re.compile("entity_id:\s*((air_quality|alarm_control_panel|alert|automation|binary_sensor|button|calendar|camera|climate|counter|device_tracker|fan|group|humidifier|input_boolean|input_number|input_select|light|media_player|number|person|proximity|scene|script|select|sensor|sun|switch|timer|vacuum|weather|zone)\.[A-Za-z_0-9]*)")
        self.service_pattern = re.compile("service:\s*([A-Za-z_0-9]*\.[A-Za-z_0-9]*)")
        self.included_folders = self.args.get('included_folders', ['/config'])
        if not isinstance(self.included_folders, list) or len(self.included_folders) == 0:
            self.throw_error(f"included_folders parameter in {APP_CFG_PATH} should be a list with at least 1 folder in it")
        self.excluded_folders =  self.args.get('excluded_folders', [])
        if not isinstance(self.excluded_folders, list):
            self.throw_error(f"excluded_folders parameter in {APP_CFG_PATH} should be a list not single value")
        self.report_header = self.args.get('report_header', '=== Watchman Report ===')
        # large reports are divided into chunks (size in bytes) as notification services may reject very long messages
        self.chunk_size = self.args.get('chunk_size', 3500)
        self.notify_service = self.args.get('notify_service', None)

        if not self.notify_service or not self.notify_service in self.load_services():
            self.throw_error(f'{self.notify_service} cannot be used as notify_service parameter in {APP_CFG_PATH}, an active notification service should be specified, e.g. notify.telegram')
        else:
            self.log(f'Notificaton service: {self.notify_service}', level="DEBUG")
            self.notify_service = self.notify_service.replace('.','/')

        self.ignore = self.args.get('ignore', [])
        if not isinstance(self.ignore, list):
            self.throw_error(f"ignore parameter in {APP_CFG_PATH} should be a list")

        self.ignored_states = self.args.get('ignored_states', [])
        if not isinstance(self.ignored_states, list):
            self.throw_error(f"ignored_states parameter in {APP_CFG_PATH} should be a list")

        self.listen_event(self.on_event, event="ad.watchman.audit")
        #self.audit(ignored_states = self.ignored_states)

    def on_event(self, event_name, data, kwargs):
        self.audit(ignored_states = self.ignored_states)

    def throw_error(self, msg):
        self.call_service("persistent_notification/create", title = f"Invalid {APP_NAME} config", message = msg )
        raise Exception(msg)

    def load_services(self):
        services = []
        service_data = self.list_services(namespace="global")
        for s in service_data:
            services.append(f"{s['domain']}.{s['service']}")
        return services

    def audit(self, ignored_states = []):
        start_time = time.time()
        entity_list, service_list, files_parsed = utils.parse(self.included_folders, self.excluded_folders, self)
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
            report += f"\nMissing {len(services_missing)} service(-s) from {len(service_list)} found in your config:\n"
            for service in services_missing: 
                report += f"{service} found in {service_list[service]}\n"
                if len(report) > self.chunk_size:
                    report_chunks.append(report)
                    report = ""
        else:
            report += f"\nCongratulations, all {len(service_list)} services from your config are available!\n"

        if entities_missing:
            report += f"\nMissing {len(entities_missing)} entity(-es) from {len(entity_list)} found in your config:\n"
            for entity in entities_missing:
                state = self.get_state(entity) or 'missing'
                report += f"{entity}[{state}] in: {entity_list[entity]}\n"
                if len(report) > self.chunk_size:
                    report_chunks.append(report)
                    report = ""
        else:
            report += f"\nCongratulatiions, all {len(entity_list)} entities from your config are available!"

        report += f"\nParsed {files_parsed} yaml files in {(time.time()-start_time):.2f} s."
        report_chunks.append(report)

        report_file = open('/config/watchman_report.txt', "w")
        for chunk in report_chunks:
            report_file.write(chunk)
        report_file.close()
                        
        if entities_missing or services_missing:
            self.send_notification(report_chunks)

    def send_notification(self, report):
        #todo check exception
        for chunk in report:
            self.call_service(self.notify_service, message=chunk)

