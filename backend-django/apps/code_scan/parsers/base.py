from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseParser(ABC):
    """
    Base class for all scan result parsers
    """
    
    @abstractmethod
    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Parse the report file and return a list of defects.
        
        Expected return format:
        [
            {
                "file_path": str,
                "line_number": int,
                "defect_type": str,
                "severity": str ("High", "Medium", "Low"),
                "description": str,
                "help_info": str,  # Optional
                "code_snippet": str, # Optional
            },
            ...
        ]
        """
        pass
