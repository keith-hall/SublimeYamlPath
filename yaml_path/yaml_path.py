from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.scanner import ScannerError
from ruamel.yaml.parser import ParserError
from typing import Iterable, Optional, Union
import re


UNQUOTED_KEY_REGEX = re.compile(r"^[a-zA-Z0-9_][a-zA-Z0-9_]*$")


def parse_yaml_docs(text: str) -> Union[Iterable[Union[CommentedMap, CommentedSeq]], ScannerError, ParserError]:
    try:
        yaml_docs = list(YAML().load_all(text))
    except ScannerError as e:
        return e
    except ParserError as e:
        return e

    return yaml_docs


def yaml_path_to(yaml_docs: Iterable[Union[CommentedMap, CommentedSeq]], offset_line: int, offset_col: int) -> str:
    for yaml in yaml_docs:
        if not yaml: # document could be empty i.e. None
            continue
        result = None
        if isinstance(yaml, CommentedMap):
            result = recursive_search_offset_map(yaml, offset_line, offset_col, [])
        elif isinstance(yaml, CommentedSeq):
            result = recursive_search_offset_seq(yaml, offset_line, offset_col, [])
        if result:
            return breadcrumbs_to_path(result)
    return ''


def breadcrumbs_to_path(breadcrumbs: Iterable[Union[str, int]]) -> str:
    path = ''
    if not breadcrumbs:
        return path

    for item in breadcrumbs:
        if isinstance(item, str):
            if UNQUOTED_KEY_REGEX.match(item):
                if path:
                    path += '.'
                path += item
            else:
                key = item.replace('"', '\\"')
                path += '["' + key + '"]'
        else:
            path += '[' + str(item) + ']'
    return path


def recursive_search_offset_map(yaml: CommentedMap, offset_line: int, offset_col: int, stack: list) -> Optional[list]:
    # here we skip the recursive search for nodes which don't contain the relevant offset
    closest_item = None
    for item in yaml.keys():
        subitem_pos = get_position_of_subitem(yaml, item)
        if subitem_pos[0] <= offset_line:
            closest_item = item
        elif subitem_pos[0] > offset_line:
            break

    if closest_item is not None:
        result = recursive_search_offset_subitem(yaml, closest_item, offset_line, offset_col, stack)
        if result:
            return result

    return None


def recursive_search_offset_seq(yaml: CommentedSeq, offset_line: int, offset_col: int, stack: list) -> Optional[list]:
    # here we skip the recursive search for nodes which don't contain the relevant offset
    closest_index = None
    for index in range(0, len(yaml)):
        subitem_pos = get_position_of_subitem(yaml, index)
        if subitem_pos[0] <= offset_line:
            closest_index = index
        elif subitem_pos[0] > offset_line:
            break

    if closest_index is not None:
        result = recursive_search_offset_subitem(yaml, closest_index, offset_line, offset_col, stack)
        if result:
            return result

    return None


def recursive_search_offset_subitem(
    yaml: Union[CommentedMap, CommentedSeq],
    subitem: Union[str, int],
    offset_line: int,
    offset_col: int,
    stack: list
) -> Optional[list]:

    position_of_item = get_position_of_subitem(yaml, subitem)
    line_number_of_item = position_of_item[0]
    new_stack = stack[:] + [subitem]
    
    if line_number_of_item == offset_line:
        # TODO: for now we are not checking column
        return new_stack
    elif line_number_of_item > offset_line:
        # already past the line we are interested in
        return None
    elif isinstance(yaml[subitem], CommentedMap):
        if result := recursive_search_offset_map(yaml[subitem], offset_line, offset_col, new_stack):
            return result
    elif isinstance(yaml[subitem], CommentedSeq):
        if result := recursive_search_offset_seq(yaml[subitem], offset_line, offset_col, new_stack):
            return result
    return None


def get_position_of_subitem(
    yaml: Union[CommentedMap, CommentedSeq],
    subitem: Union[str, int],
) -> tuple: #[int, int]:
    return yaml.lc.key(subitem) if isinstance(yaml, CommentedMap) else yaml.lc.item(subitem)
