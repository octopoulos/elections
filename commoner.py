# coding: utf-8
# @author octopoulo <polluxyz@gmail.com>
# @version 2020-11-24

"""
Common functions
"""

import errno
import json
import logging
import os
from platform import system
import re
from typing import Any


def clamp(number: int or float, low: int or float, high: int or float) -> int or float:
    """Clamp a number
    """
    if number < low:
        return low
    if number > high:
        return high
    return number


def makedirs_safe(folder: str) -> bool:
    """Create a folder recursively + handle errors
    :return: True if the folder has been created or existed already, False otherwise
    """
    if not folder:
        return True

    try:
        os.makedirs(folder)
        return True
    except Exception as e:
        if isinstance(e, OSError) and e.errno == errno.EEXIST:
            return True
        logging.error({'status': 'makedirs_safe__error', 'error': e, 'folder': folder})
        return False


def open_json_file(filename: str, locked: bool=False) -> Any:
    """Read the content of a file and return the JSON of that content, empty {} if failed
    """
    if not (data := read_text_safe(filename, locked=locked)):
        return {}
    try:
        return json.loads(data)
    except ValueError as e:
        logging.error({'status': 'open_json_file__error', 'error': e})
        return {}


def read_text_safe(filename: str, locked: bool=False, want_bytes: bool=False) -> str or bytes or None:
    """Read the content of a file and convert it to utf-8
    """
    if not filename or not os.path.isfile(filename):
        return None

    try:
        open_func = open
        with open_func(filename, 'rb') as file:
            data = file.read()
            return data if want_bytes else data.decode('utf-8-sig')
    except OSError as e:
        logging.error({'status': 'read_text_safe__error', 'error': e, 'filename': filename})
    return None


def save_json_file(
        filename: str,
        data: Any,
        locked: bool=False,                 # lock the file during saving?
        ascii_: bool=False,
        indent: int=0,                      # 4
        precision: int=-1,                  # float precision
        sort: bool=False,                   # True
        convert_newlines: bool=False,
        one_line: bool=False,               # 1 line per data
        ) -> bool:                          # True on success, False on error
    """Encode data to json and save it
    """
    try:
        code = json.dumps(data, ensure_ascii=ascii_, indent=indent, sort_keys=sort)
        if one_line and (code := code.replace('","', '",\n"')):
            if code[0] == '{':
                code = code[0] + '\n' + code[1:]
            if code[-1] == '}':
                code = code[:-1] + '\n}'
        return write_text_safe(filename, code, locked=locked, convert_newlines=convert_newlines)
    except Exception as e:
        logging.error({'status': 'save_json_file__invalid_data', 'error': e})
        return False


def write_text_safe(
        filename: str,
        data: str or bytes,
        mode: str='wb',
        locked: bool=False,
        convert_newlines: bool=False,           # convert \n to \r\n on windows
        ) -> bool:
    """Save text or binary to a file
    """
    if not filename or '?' in filename:
        return False

    # windows support
    if convert_newlines and isinstance(data, str) and system() == 'Windows' and '\r\n' not in data:
        data = data.replace('\n', '\r\n')

    # save
    path = os.path.dirname(filename)
    if not makedirs_safe(path):
        return False

    try:
        open_func = locked_open if locked else open
        with open_func(filename, mode) as file:
            if data:
                file.write(data.encode('utf-8') if isinstance(data, str) else data)
            return True
    except OSError as e:
        logging.error({'status': 'write_text_safe__error', 'error': e, 'filename': filename})
    return False
