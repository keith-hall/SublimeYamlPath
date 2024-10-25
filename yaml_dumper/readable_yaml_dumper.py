import json
from ruamel.yaml.dumper import Dumper
from ruamel.yaml import YAML


# inspired by https://stackoverflow.com/a/40044739/4473405
def represent_str(dumper: Dumper, str_data: str) -> str:
    tag = 'tag:yaml.org,2002:str'
    style = None
    
    str_data = str_data.strip()

    if '\n' in str_data:
        style = '|'
    elif (str_data.startswith('{') and str_data.endswith('}')) or (str_data.startswith('[') and str_data.endswith(']')): # maybe a JSON dict or sequence
        style = '|'
        try:
            #str_data = json.dumps(json.loads(str_data), indent=2)
            data = json.loads(str_data)
            return represent_dict(dumper, data)
        except:
            # data wasn't valid JSON, just leave it unprettified
            pass
    elif str_data.startswith('"{') and str_data.endswith('}"'): # maybe a string containing a JSON serialized dict
        try:
            data = json.loads(json.loads(str_data))
            return represent_dict(dumper, data)
            #return dumper.represent_mapping('tag:yaml.org,2002:map', data, flow_style=False)
            #data = json.dumps(data, indent=2)
        except:
            # data wasn't valid JSON, just leave it unprettified
            style = '|'
            pass
    elif str_data.startswith('"') and str_data.endswith('"'): # maybe a JSON string
        style = '|'
        try:
            str_data = json.loads(data)
        except:
            # data wasn't valid JSON, just leave it unprettified
            pass

    return dumper.represent_scalar(tag, str_data, style=style)


def represent_dict(dumper: Dumper, data: dict) -> str:
    return dumper.represent_mapping('tag:yaml.org,2002:map', data, flow_style=False)


def configure_yaml_for_dumping(yaml: YAML):
    yaml.representer.add_representer(str, represent_str)
    yaml.representer.add_representer(dict, represent_dict)
    yaml.default_flow_style = False
