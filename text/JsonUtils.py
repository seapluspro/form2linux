'''
JsonUtils.py

Created on: 20.08.2023
    Author: SeaPlusPro
   License: CC0 1.0 Universal
'''
import re
#from typing import Sequence

# ...................................1.....1.2............2
REG_EXPR_FLOAT_LIST = re.compile(r'^[-+0-9.,;: eE]+$')


def checkJsonNodeType(specifiedType: str, node) -> str:
    '''Checks whether a node has a given type.
    @param specifiedType: the expected type
    @param node: the node to test
    @return None: success. Otherwise: the error message
    '''
    rc = None
    realType = type(node)
    if specifiedType == 'i':
        if realType is not int:
            rc = 'is not an integer'
    elif specifiedType == 'b':
        if realType is not bool:
            rc = 'is not a boolean'
    elif specifiedType == 'f':
        if realType is not float and realType is not int:
            rc = 'is not a float'
    elif specifiedType == 'F':
        if realType is not str or not REG_EXPR_FLOAT_LIST.match(node):
            rc = 'is not a float list'
    elif specifiedType == 's':
        if realType is not str:
            rc = 'is not a string'
    elif specifiedType == 'a':
        if realType is not list:
            rc = 'is not a list'
    elif specifiedType == 'm':
        if realType is not dict:
            rc = 'is not a map'
    if rc is not None:
        rc = f'{printableJsonNode(node)} {rc}'
    return rc


def checkJsonMap(jsonTree, neededAttributes: str, strict: bool=False, optionalAttributes: str=None) -> str:
    '''Checks the structure of a Json list.
    @param jsonTree: the Json tree node to inspect
    @param neededAttributes: a blank delimited list of attribute definitions:
        An attribute definition is a string with the syntax <em>name:type</em>, e.g. "id name vertices"
        Type: s: string b: bool i: integer f: floating number F: floating number list m: json object (map) a: json object (array)
        Example "id:i name:s list:a"
    @param strict: <em>True</em>: the map may contain only attribute listed 
        in <em>neededAttributes</em> and <em>optionalAttributes</em>
    @param optionalAttributes: a blank delimited list of attribute definitions optional in the Json object.
        The syntax is like that in <em>neededAttributes</em>
    @return None: success Otherwise: an error message
    '''
    rc = None
    missing = None
    wrong = ''

    def checkType(specifiedType: str, node):
        msg = checkJsonNodeType(specifiedType, node)
        return '' if msg is None else f'\n{msg}'
    neededList = {}
    if neededAttributes is not None:
        for definition in neededAttributes.split(' '):
            neededList[definition[0:-2]] = definition[-1]
        for key, neededType in neededList.items():
            if key not in jsonTree:
                if missing is None:
                    missing = f'missing attribute(s): {key}'
                else:
                    missing += f' {key}'
            else:
                item = jsonTree[key]
                wrong += checkType(neededType, item)
    optionalList = {}
    if optionalAttributes is not None:
        for definition in optionalAttributes.split(' '):
            optionalList[definition[0:-2]] = definition[-1]
        for key, optionalType in optionalList.items():
            if key in jsonTree:
                item = jsonTree[key]
                wrong += checkType(optionalType, item)
    if strict:
        for key in jsonTree.keys():
            if key not in neededList and key not in optionalList:
                wrong += f" unknown attribute: {key}"
    if missing is not None or wrong != '':
        rc = wrong[1:] if missing is None else (
            missing if wrong == '' else missing + "\n" + wrong)
    return rc


def checkJsonMapAndRaise(jsonTree, neededAttributes: str, strict: bool=False, optionalAttributes: str=None) -> str:
    '''Checks the structure of a Json list. Raise an exception on error.
    @param jsonTree: the Json tree node to inspect
    @param neededAttributes: a blank delimited list of attribute definitions:
        An attribute definition is a string with the syntax <em>name:type</em>, e.g. "id name vertices"
        Type: s: string b: bool i: integer f: floating number 
            F: floating number list m: json object (map) a: json object (array)
        Example "id:i name:s list:a"
    @param strict: <em>True</em>: the map may contain only attribute listed in 
        <em>neededAttributes</em> and <em>optionalAttributes</em>
    @param optionalAttributes: a blank delimited list of attribute definitions optional in the Json object.
        The syntax is like that in <em>neededAttributes</em>
    '''
    msg = checkJsonMap(jsonTree, neededAttributes, strict, optionalAttributes)
    if msg is not None:
        raise ValueError(f'Json format error: {msg}')


def checkJsonPath(jsonTree, path: str, nodeType: str):
    '''Checks whether a path in the Json tree exists.
    @param jsonTree: the Json tree node to inspect
    @param path: a blank delimited list of attribute names. Example "person name firstName"
    @param nodeType: the type of the last node:
        Type: s: string i: integer f: floating number F: floating number list m: json object (map) a: json object (array)
    '''
    rc = None
    keys = path.split(' ')
    chain = ''
    current = jsonTree
    for key in keys:
        if key.startswith('['):
            index = int(key[1:-1])
            if not isinstance(current, list):
                rc = f'not a list path: {path} current: {current}'
            elif index < 0 or index >= len(current):
                rc = f'wrong index {index} / {len(current)}'
            else:
                current = current[index]
        elif key not in current:
            rc = f'missing Json node "{key}" in {chain[1:]}'
            break
        else:
            current = current[key]
        chain += f'.{key}'
    if rc is None:
        rc = checkJsonNodeType(nodeType, current)
    return rc


def nodeOfJsonTree(jsonTree, path: str, nodeType: str, mayBeAbsent: bool=False):
    '''Returns a specified node in a givne Json tree.
    @param jsonTree: the Json tree
    @param path: a blank delimited list of node names, e.g. "Person Name"
    @param nodeType: the expected type of the node, e.g. "m" for "map"
    @param mayBeAbsent: <em>True</em>: return None if not found. Otherwise an exception is raised
    @return None: the path does not exist. Otherwise: The node value
    '''
    msg = checkJsonPath(jsonTree, path, nodeType)
    if msg is not None:
        if not mayBeAbsent:
            raise ValueError(f'Json tree problem: {msg}')
        path = None
    rc = None
    if path is not None:
        nodes = path.split(' ')
        rc = jsonTree
        for node in nodes:
            if node.startswith('['):
                index = int(node[1:-1])
                rc = rc[index]
            else:
                rc = rc[node]
    return rc


def optionalBoolNode(jsonTree, path: str, defaultValue: bool=False) -> bool:
    '''Gets the value of a json tree node with the type boolean. The node may not exist.
    @param jsonTree: The tree to inspect.
    @param path: A blank delimited list of node names
    @param defaultValue: The result if the node does not exist.
    @return <em>defaultValue</em>: the specified node does not exist. Otherwise: the value of the node.
    '''
    rc = nodeOfJsonTree(jsonTree, path, 'b', True)
    if rc is None:
        rc = defaultValue
    return rc


def optionalIntNode(jsonTree, path: str, defaultValue: float=None) -> float:
    '''Gets the value of a json tree node with the type int. The node may not exist.
    @param jsonTree: The tree to inspect.
    @param path: A blank delimited list of node names
    @param defaultValue: The result if the node does not exist.
    @return <em>defaultValue</em>: the specified node does not exist. Otherwise: the value of the node.
    '''
    rc = nodeOfJsonTree(jsonTree, path, 'i', True)
    if rc is None:
        rc = defaultValue
    return rc


def optionalFloatNode(jsonTree, path: str, defaultValue: float=None) -> float:
    '''Gets the value of a json tree node with the type float. The node may not exist.
    @param jsonTree: The tree to inspect.
    @param path: A blank delimited list of node names
    @param defaultValue: The result if the node does not exist.
    @return <em>defaultValue</em>: the specified node does not exist. Otherwise: the value of the node.
    '''
    rc = nodeOfJsonTree(jsonTree, path, 'f', True)
    if rc is None:
        rc = defaultValue
    return rc


def printableJsonNode(node) -> str:
    '''Returns a string characteristic for a given Json tree node.
    @param node: the node to inspect
    @return: a characteristic string of the node
    '''
    if node is None:
        rc = '<None>'
    else:
        theType = type(node)
        if theType is str:
            rc = f'"{node}"' if len(node) <= 40 else f'"{node[0:39]}..."'
        elif theType is bool or theType is int or theType is float:
            rc = f'{node}'
        elif theType is list:
            rc = '[..]'
        elif theType is dict:
            rc = '{..}'
        else:
            rc = f'<{node}>'
    return rc
