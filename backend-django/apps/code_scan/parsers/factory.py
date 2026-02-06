from typing import Type
from .base import BaseParser
from .tscan_parser import TScanParser
from .cppcheck_parser import CppCheckParser

class ParserFactory:
    _parsers = {
        'tscan': TScanParser,
        'cppcheck': CppCheckParser,
    }
    
    @classmethod
    def get_parser(cls, tool_name: str) -> BaseParser:
        parser_cls = cls._parsers.get(tool_name.lower())
        if not parser_cls:
            raise ValueError(f"No parser found for tool: {tool_name}")
        return parser_cls()
