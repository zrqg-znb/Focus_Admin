import json
import xml.etree.ElementTree as ET
from typing import List, Dict, Any
from .base import BaseParser

class TScanParser(BaseParser):
    """
    Parser for TScanCode output (supporting XML and JSON)
    """
    
    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        if file_path.endswith('.json'):
            return self._parse_json(file_path)
        elif file_path.endswith('.xml'):
            return self._parse_xml(file_path)
        else:
            raise ValueError("Unsupported file format for TScan. Expected .xml or .json")

    def _parse_json(self, file_path: str) -> List[Dict[str, Any]]:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        results = []
        # TScan JSON format assumption (adjust based on actual output)
        # Assuming list of dicts directly or under a 'defects' key
        items = data.get('defects', data) if isinstance(data, dict) else data
        
        for item in items:
            results.append({
                "file_path": item.get('file', 'unknown'),
                "line_number": int(item.get('line', 0)),
                "defect_type": item.get('type', 'Unknown'),
                "severity": self._map_severity(item.get('severity')),
                "description": item.get('message', ''),
                "help_info": item.get('help_info', ''),  # Assuming JSON might have this
                "code_snippet": item.get('code', ''),
            })
        return results

    def _parse_xml(self, file_path: str) -> List[Dict[str, Any]]:
        tree = ET.parse(file_path)
        root = tree.getroot()
        results = []
        
        # TScan XML format assumption: <error file="..." line="..." id="..." severity="..." msg="..."/>
        for error in root.findall('.//error'):
            results.append({
                "file_path": error.get('file', 'unknown'),
                "line_number": int(error.get('line', 0)),
                "defect_type": error.get('id', 'Unknown'),
                "severity": self._map_severity(error.get('severity')),
                "description": error.get('msg', ''),
                "help_info": error.get('sub_msg', ''), # Sometimes additional info is here
                "code_snippet": "", # XML might not have code snippet
            })
        return results

    def _map_severity(self, severity_str: str) -> str:
        """Map tool severity to standard High/Medium/Low"""
        if not severity_str:
            return 'Low'
        s = severity_str.lower()
        if s in ['1', 'high', 'critical', 'error']:
            return 'High'
        elif s in ['2', 'medium', 'warning']:
            return 'Medium'
        return 'Low'
