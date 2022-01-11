import glob
import os
import re

def folder_included(path, excluded_folders):
    for folder in excluded_folders:
        if folder in path:
            return False
    return True

def get_next_file(folder_list, excluded_folders):
    for folder in folder_list:
        root = os.path.join(folder, '**/*.yaml')
        for filename in glob.iglob(root, recursive=True):
            if folder_included(filename, excluded_folders):
                yield filename

def add_entry(_list, entry, yaml_file, lineno):
    if entry in _list:
        if yaml_file in _list[entry]: 
            _list[entry].get(yaml_file, []).append(lineno)
    else:
        _list[entry] = {yaml_file: [lineno]}

def parse(folders, excluded_folders, logger=None):
    files_parsed = 0
    entity_pattern = re.compile("(?:(?<=\s)|(?<=^)|(?<=\")|(?<=\'))([A-Za-z_0-9]*\s*:)?(?:\s*)?((air_quality|alarm_control_panel|alert|automation|binary_sensor|button|calendar|camera|climate|counter|device_tracker|fan|group|humidifier|input_boolean|input_number|input_select|light|media_player|number|person|proximity|scene|script|select|sensor|sun|switch|timer|vacuum|weather|zone)\.[A-Za-z_*0-9]+)")
    service_pattern = re.compile("service:\s*([A-Za-z_0-9]*\.[A-Za-z_0-9]+)")
    entity_list = {}
    service_list = {}
    for yaml_file in get_next_file(folders, excluded_folders):
        #if logger:
        #    logger.log(f'opening {yaml_file} file', level="DEBUG")
        files_parsed += 1
        for i, line in enumerate(open(yaml_file)):
            if line.strip().startswith('#'):
                continue
            for match in re.finditer(entity_pattern, line):
                typ, val = match.group(1), match.group(2)
                if typ != "service:" and "*" not in val and not val.endswith('.yaml'):
                    add_entry(entity_list, val, yaml_file, i+1)
            for match in re.finditer(service_pattern, line):
                val = match.group(1)
                add_entry(service_list, val, yaml_file, i+1)
    if logger:
        logger.log(f"Parsed {files_parsed} files.")
    return (entity_list, service_list, files_parsed)
