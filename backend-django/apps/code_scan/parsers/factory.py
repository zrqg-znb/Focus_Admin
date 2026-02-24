from typing import Type
from .base import BaseParser
from .tscan_parser import TScanParser
from .cppcheck_parser import CppCheckParser
from .weggli_parser import WeggliParser
from .cooddy_parser import CooddyParser
from .binexplorer_parser import BinExplorerParser
from .clang_tidy_parser import ClangTidyParser

class ParserFactory:
    _parsers = {
        'tscan': TScanParser,
        'cppcheck': CppCheckParser,
        'weggli': WeggliParser,
        'cooddy': CooddyParser,
        'binexplorer': BinExplorerParser,
        'binexplorer_scan': BinExplorerParser,
        'clang-tidy': ClangTidyParser,
        'clang_tidy': ClangTidyParser,
        'clangtidy': ClangTidyParser,
    }
    
    @classmethod
    def get_parser(cls, tool_name: str) -> BaseParser:
        parser_cls = cls._parsers.get(tool_name.lower())
        if not parser_cls:
            raise ValueError(f"No parser found for tool: {tool_name}")
        return parser_cls()
