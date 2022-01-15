#encoding: utf-8
'''Watchman AppDaemon application module'''
import os
import time
import fnmatch
import appdaemon.plugins.hass.hassapi as hass
import utils

APP_NAME = "watchman"
APP_CFG_PATH = "/config/appdaemon/apps/watchman/watchman.yaml"
EVENT_NAME = "ad.watchman.audit"
APP_FOLDER = "/config/appdaemon/apps/watchman"

class Watchman(hass.Hass):
    '''Watchman AppDaemon application'''
    def initialize(self):
        '''Runs when application (re-)started'''
        self.check_lovelace = self.args.get('lovelace_ui', False)
        self.debug_log = self.args.get('debug_log', False)
        self.included_folders = self.args.get('included_folders', ['/config'])

        if not isinstance(self.included_folders, list) or len(self.included_folders) == 0:
            self.p_notification(f"invalid {APP_NAME} config",
            f"`included_folders` parameter in `{APP_CFG_PATH}` should be "
            "a list with at least 1 folder in it", error=True)
        else:
            for i, folder in enumerate(self.included_folders):
                self.included_folders[i] = os.path.join(folder, '**/*.yaml')
            if self.check_lovelace:
                self.included_folders.append('/config/.storage/**/lovelace*')

        self.excluded_folders =  self.args.get('excluded_folders', [])

        if not isinstance(self.excluded_folders, list):
            self.p_notification(f"invalid {APP_NAME} config",
            f"`excluded_folders` parameter in `{APP_CFG_PATH}` should be "
            "a list not single value", error=True)
        self.report_header = self.args.get('report_header', '=== Watchman Report ===')

        # large reports are divided into chunks (size in bytes) as notification services
        # may reject very long messages
        self.chunk_size = self.args.get('chunk_size', 3500)
        self.notify_service = self.args.get('notify_service', None)

        self.ignored_items = self.args.get('ignored_items', [])
        if not isinstance(self.ignored_items, list):
            self.p_notification(f"invalid {APP_NAME} config",
            f"`ignored_items` parameter in `{APP_CFG_PATH}` should be a list",
            error=True)

        self.ignored_states = self.args.get('ignored_states', [])
        if not isinstance(self.ignored_states, list):
            self.p_notification(f"invalid {APP_NAME} config",
            f"`ignored_states` parameter in `{APP_CFG_PATH}` should be a list", error=True)

        self.report_path = self.args.get('report_path', '/config/watchman_report.txt')

        folder, _ = os.path.split(self.report_path)
        if not os.path.exists(folder):
            self.p_notification("Error from watchman",
            f"Incorrect `report_path` {self.report_path}.", error=True)

        if not self.get_flag('.skip_greetings'):
            self.set_flag('.skip_greetings')
            self.p_notification("Hello from watchman!",
            "Congratulations, watchman is up and running!\n\n "
            f"Please adjust `{APP_CFG_PATH}` config file according "
            "to your needs or just go to Developer Tools->Events "
            f"and fire up `{EVENT_NAME}` event.")

        self.listen_event(self.on_event, event=EVENT_NAME)
        #self.audit(ignored_states = self.ignored_states)

    def p_notification(self, title, msg, error=False):
        '''Display a persistent notification in Home Assistant'''
        self.call_service("persistent_notification/create", title = title, message = msg )
        if error:
            raise Exception(msg)

    def on_event(self, event_name, data, kwargs):
        '''Process ad.watchman.audit event'''
        create_file = data.get("create_file", True)
        send_notification = data.get("send_notification", True)
        self.audit(create_report_file = create_file, notification = send_notification,
        ignored_states = self.ignored_states)

    def load_services(self):
        '''Load all available services from HA registry'''
        services = []
        service_data = self.list_services(namespace="global")
        for srv in service_data:
            services.append(f"{srv['domain']}.{srv['service']}")
        return services

    def debug(self, msg):
        '''Debug logging'''
        if self.debug_log:
            self.log(msg)

    def audit(self, create_report_file, notification, ignored_states = None):
        '''Perform audit of entities and services'''
        if ignored_states is None:
            ignored_states = []
        start_time = time.time()
        entity_list, service_list, files_parsed = utils.parse(self.included_folders,
        self.excluded_folders, self)
        self.log(f"Found {len(entity_list)} entities, {len(service_list)} services ")
        if files_parsed == 0:
            self.log('No yaml files found, please check apps.yaml config', level="ERROR")
            self.p_notification("Error from watchman!",
                                "No automation files found, please check apps.yaml config")
            return

        entities_missing = {}
        services_missing = {}
        service_registry = self.load_services()

        excluded_entities = []
        excluded_services = []
        for glob in self.ignored_items:
            if glob:
                excluded_entities.extend(fnmatch.filter(entity_list, glob))
                excluded_services.extend(fnmatch.filter(service_list, glob))

        for entity, occurences in entity_list.items():
            if entity in service_registry: #this is a service, not entity
                continue
            state = self.get_state(entity)
            if not state and state != "":
                state = 'missing'
            if state in ignored_states:
                continue
            if state in ['missing', 'unknown', 'unavailable']:
                if entity in excluded_entities:
                    self.debug(f"Ignored entity: {entity}")
                    continue
                else:
                    entities_missing[entity] = occurences
        for service, occurences in service_list.items():
            if service not in service_registry:
                if service in excluded_services:
                    self.debug(f"Ignored service: {service}")
                    continue
                else:
                    services_missing[service] = occurences

        self.set_state("sensor.watchman_missing_entities", state=len(entities_missing))
        self.set_state("sensor.watchman_missing_services", state=len(services_missing))

        report_chunks = []

        report = ""
        report += f"{self.report_header} \n"

        if services_missing:
            report += f"\n=== Missing {len(services_missing)} service(-s) from "
            report += f"{len(service_list)} found in your config:\n"
            for service in services_missing:
                report += f"{service} in {service_list[service]}\n"
                if len(report) > self.chunk_size:
                    report_chunks.append(report)
                    report = ""
        elif len(service_list) > 0:
            report += f"\n=== Congratulations, all {len(service_list)} services from "
            report += "your config are available!\n"
        else:
            report += "\n=== No services found in configuration files!\n"

        if entities_missing:
            report += f"\n=== Missing {len(entities_missing)} entity(-es) from "
            report += f"{len(entity_list)} found in your config:\n"
            for entity in entities_missing:
                state = self.get_state(entity) or 'missing'
                report += f"{entity}[{state}] in: {entity_list[entity]}\n"
                if len(report) > self.chunk_size:
                    report_chunks.append(report)
                    report = ""
        elif len(entity_list) > 0:
            report += f"\n=== Congratulatiions, all {len(entity_list)} entities from "
            report += "your config are available!\n"
        else:
            report += "\n=== No entities found in configuration files!\n"

        report += f"\n=== Parsed {files_parsed} yaml files in "
        report += f"{(time.time()-start_time):.2f} s. on {time.strftime('%d %b %Y %H:%M:%S')}"
        report_chunks.append(report)

        if create_report_file:
            if not self.get_flag('.skip_achievement'):
                self.set_flag('.skip_achievement')
                self.p_notification("Achievement unlocked: first report!",
                f"Your first report was stored in `{self.report_path}` \n\n "
                "TIP: set `notify_service` parameter in configuration file to "
                "receive report via notification service of choice. \n\n "
                "This is one-time message, it will not bother you in the future.")

            report_file = open(self.report_path, "w", encoding="utf-8")
            for chunk in report_chunks:
                report_file.write(chunk)
            report_file.close()
        if notification:
            if (entities_missing or services_missing):
                self.send_notification(report_chunks)
            else:
                self.log("Entities and services are fine, no notification required")

    def send_notification(self, report):
        '''Send audit report via a notification service'''
        if not self.notify_service in self.load_services():
            self.p_notification(f"invalid {APP_NAME} config",
            f"{self.notify_service} service was not found in service registry. "
            f"Please specify a valid notification service, e.g. `notify.telegram`", error=True)
        elif not self.notify_service:
            self.p_notification(f"invalid {APP_NAME} config",
            f"Set `notify_service` parameter in `{APP_CFG_PATH}`, to a notification "
            "service, e.g. `notify.telegram`", error=True)
        for chunk in report:
            self.call_service(self.notify_service.replace('.','/'), message=chunk)

    def set_flag(self, flag):
        '''Set persistent flag'''
        report_file = open(os.path.join(APP_FOLDER, flag), "w", encoding="utf-8")
        report_file.close()

    def get_flag(self, flag):
        '''Get persistent flag'''
        return os.path.exists(os.path.join(APP_FOLDER, flag))
