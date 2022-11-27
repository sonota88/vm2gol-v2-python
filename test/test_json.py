import json
import sys

def read_file(path):
    text = ""
    with open(path) as f:
        for line in f:
            text += line
    return text

def to_json(data):
    return json.dumps(data, indent=2)

def parse_json(json_):
    return json.loads(json_)

in_file = sys.argv[1]
json_str = read_file(in_file)

print(to_json(parse_json(json_str)))
