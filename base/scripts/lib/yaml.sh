#!/bin/bash
# =============================================================================
# AiClipse YAML Library
# Parse YAML files using Python (always available in our containers)
# =============================================================================

set -euo pipefail

# =============================================================================
# yaml_get - Get a single value from YAML
# Usage: yaml_get "config.yaml" "name"
#        yaml_get "config.yaml" "models.0.repo"
# =============================================================================
yaml_get() {
    local file="$1"
    local key="$2"
    
    python3 -c "
import yaml
import sys

try:
    with open('$file') as f:
        data = yaml.safe_load(f)
    
    # Navigate nested keys (supports dot notation and array indices)
    keys = '$key'.replace('[', '.').replace(']', '').split('.')
    
    for k in keys:
        if data is None:
            break
        if k.isdigit():
            data = data[int(k)] if isinstance(data, list) and len(data) > int(k) else None
        else:
            data = data.get(k) if isinstance(data, dict) else None
    
    if data is not None:
        print(data)
except Exception as e:
    print(f'Error: {e}', file=sys.stderr)
    sys.exit(1)
"
}

# =============================================================================
# yaml_list - Iterate over a YAML array, outputting each item as JSON
# Usage: yaml_list "config.yaml" "models" | while read -r item; do ... done
# =============================================================================
yaml_list() {
    local file="$1"
    local key="$2"
    
    python3 -c "
import yaml
import json
import sys

try:
    with open('$file') as f:
        data = yaml.safe_load(f)
    
    # Navigate to the key
    keys = '$key'.split('.') if '$key' else []
    for k in keys:
        if data is None:
            break
        data = data.get(k) if isinstance(data, dict) else None
    
    # Output each item as JSON line
    if isinstance(data, list):
        for item in data:
            print(json.dumps(item))
    elif data is not None:
        print(json.dumps(data))
except Exception as e:
    print(f'Error: {e}', file=sys.stderr)
    sys.exit(1)
"
}

# =============================================================================
# yaml_keys - Get all keys at a level
# Usage: yaml_keys "config.yaml" "models.0"
# =============================================================================
yaml_keys() {
    local file="$1"
    local key="${2:-}"
    
    python3 -c "
import yaml
import sys

try:
    with open('$file') as f:
        data = yaml.safe_load(f)
    
    # Navigate to the key if provided
    if '$key':
        keys = '$key'.split('.')
        for k in keys:
            if data is None:
                break
            data = data.get(k) if isinstance(data, dict) else None
    
    # Output keys
    if isinstance(data, dict):
        for k in data.keys():
            print(k)
except Exception as e:
    print(f'Error: {e}', file=sys.stderr)
    sys.exit(1)
"
}

# =============================================================================
# yaml_count - Count items in a YAML array
# Usage: count=$(yaml_count "config.yaml" "models")
# =============================================================================
yaml_count() {
    local file="$1"
    local key="$2"
    
    python3 -c "
import yaml
import sys

try:
    with open('$file') as f:
        data = yaml.safe_load(f)
    
    # Navigate to the key
    keys = '$key'.split('.') if '$key' else []
    for k in keys:
        if data is None:
            break
        data = data.get(k) if isinstance(data, dict) else None
    
    if isinstance(data, list):
        print(len(data))
    elif data is not None:
        print(1)
    else:
        print(0)
except Exception as e:
    print(0)
"
}

# =============================================================================
# EXPORT FUNCTIONS
# =============================================================================
export -f yaml_get yaml_list yaml_keys yaml_count
