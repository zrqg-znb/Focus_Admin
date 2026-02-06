import xml.etree.ElementTree as ET
from typing import List, Dict, Any
from .base import BaseParser

class CppCheckParser(BaseParser):
    """
    Parser for CppCheck XML output (version 2)
    """
    
    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        return self._parse_xml(file_path)

    def _parse_xml(self, file_path: str) -> List[Dict[str, Any]]:
        tree = ET.parse(file_path)
        root = tree.getroot()
        results = []
        
        # CppCheck XML v2 format:
        # <results>
        #   <errors>
        #     <error id="..." severity="..." msg="..." verbose="..." file0="..." file="..." line="...">
        #       <location file="..." line="..."/>
        #       <symbol>...</symbol>
        #     </error>
        #   </errors>
        # </results>
        # Or sometimes directly under root for older versions
        
        errors = root.findall('.//error')
        
        for error in errors:
            # Basic attributes
            defect_type = error.get('id', 'Unknown')
            severity = self._map_severity(error.get('severity'))
            description = error.get('msg', '')
            verbose_desc = error.get('verbose', '')
            
            if verbose_desc and verbose_desc != description:
                description = f"{description}\n{verbose_desc}"

            # CppCheck errors can have multiple locations. 
            # We usually take the first one or the primary one.
            # <location> tags are preferred in v2
            locations = error.findall('location')
            
            if locations:
                # Create a result for each location? Or just the first one?
                # Usually the last location is the "error" location, others are trace.
                # But for simplicity, let's take the primary location (often the last one in trace, or the only one).
                # Actually, in CppCheck XML v2, the attributes 'file' and 'line' on <error> are deprecated/removed in favor of <location>.
                # However, if present, they are the primary location.
                
                file_path_attr = error.get('file')
                line_number_attr = error.get('line')
                
                if file_path_attr:
                     results.append({
                        "file_path": file_path_attr,
                        "line_number": int(line_number_attr) if line_number_attr else 0,
                        "defect_type": defect_type,
                        "severity": severity,
                        "description": description,
                        "help_info": "",
                        "code_snippet": "",
                    })
                else:
                    # Use the last location as it's usually the point of error
                    loc = locations[-1]
                    results.append({
                        "file_path": loc.get('file', 'unknown'),
                        "line_number": int(loc.get('line', 0)),
                        "defect_type": defect_type,
                        "severity": severity,
                        "description": description,
                        "help_info": "",
                        "code_snippet": "",
                    })
            else:
                # Fallback to attributes
                results.append({
                    "file_path": error.get('file', 'unknown'),
                    "line_number": int(error.get('line', 0)),
                    "defect_type": defect_type,
                    "severity": severity,
                    "description": description,
                    "help_info": "",
                    "code_snippet": "",
                })
                
        return results

    def _map_severity(self, severity_str: str) -> str:
        """Map tool severity to standard High/Medium/Low"""
        if not severity_str:
            return 'Low'
        s = severity_str.lower()
        if s in ['error']:
            return 'High'
        elif s in ['warning', 'performance', 'portability']:
            return 'Medium'
        elif s in ['style', 'information', 'debug']:
            return 'Low'
        return 'Low'
