'''
jsonutils.py

Created on: 20.08.2023
    Author: SeaPlusPro
   License: CC0 1.0 Universal
'''
import re
#from typing import Sequence

isUnitTest = False

JSON_UTILS_VERSION = '2023.08.20.00'
# ...................................1.....1.2............2
regExprFloatList = re.compile(r'^[-+0-9.,;: eE]+$')

def checkJsonNodeType(specifiedType: str, node):
    rc = None
    realType = type(node)
    if specifiedType  == 'i':
        if realType is not int:
            rc = 'is not an integer'
    elif specifiedType  == 'b':
        if realType is not bool:
            rc = 'is not a boolean'
    elif specifiedType  == 'f':
        if realType is not float and realType is not int:
            rc = 'is not a float'
    elif specifiedType  == 'F':
        if realType is not str or not regExprFloatList.match(node):
            rc = 'is not a float list'
    elif specifiedType  == 's':
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

def checkJsonMap(JsonTree, neededAttributes: str, strict: bool=False, optionalAttributes: str=None) -> str:
    '''Checks the structure of a Json list.
    @param JsonTree: the Json tree node to inspect
    @param neededAttributes: a blank delimited list of attribute definitions:
        An attribute definition is a string with the syntax <em>name:type</em>, e.g. "id name vertices"
        Type: s: string b: bool i: integer f: floating number F: floating number list m: json object (map) a: json object (array)
        Example "id:i name:s list:a"
    @param strict: <em>True</em>: the map may contain only attribute listed in <em>neededAttributes</em> and <em>optionalAttributes</em>
    @param optionalAttributes: a blank delimited list of attribute definitions optional in the Json object.
        The syntax is like that in <em>neededAttributes</em>
    @return None: success Otherwise: an error message
    '''
    rc = None
    missing = None
    wrong = ''
    def checkType(specifiedType: str, node, element: str):
        msg = checkJsonNodeType(specifiedType, node)
        if msg is None:
            rc2 = ''
        else:
            rc2 = f' {msg}'
        return rc2
    neededList = {}
    if neededAttributes is not None:
        for definition in neededAttributes.split(' '):
            neededList[definition[0:-2]] = definition[-1]
        for key in neededList.keys():
            neededType = neededList[key]
            if key not in JsonTree:
                if missing is None:
                    missing = f'missing attribute(s): {key}'
                else:
                    missing += f' {key}'
            else:
                item = JsonTree[key]
                item2 = printableJsonNode(item)
                wrong += checkType(neededType, item, item2)
    optionalList = {}
    if optionalAttributes is not None:
        for definition in optionalAttributes.split(' '):
            optionalList[definition[0:-2]] = definition[-1]
        for key in optionalList.keys():
            optionalType = optionalList[key]
            if key in JsonTree:
                item = JsonTree[key]
                item2 = printableJsonNode(item)
                wrong += checkType(optionalType, item, item2)
    if strict:
        for key in JsonTree.keys():
            if key not in neededList and key not in optionalList:
                wrong += f" unknown attribute: {key}"
    if missing is not None or wrong != '':
        rc = wrong[1:] if missing is None else (missing if wrong == '' else missing + "\n" + wrong)
    return rc

def checkJsonMapAndRaise(JsonTree, neededAttributes: str, strict: bool=False, optionalAttributes: str=None) -> str:
    '''Checks the structure of a Json list. Raise an exception on error.
    @param JsonTree: the Json tree node to inspect
    @param neededAttributes: a blank delimited list of attribute definitions:
        An attribute definition is a string with the syntax <em>name:type</em>, e.g. "id name vertices"
        Type: s: string b: bool i: integer f: floating number F: floating number list m: json object (map) a: json object (array)
        Example "id:i name:s list:a"
    @param strict: <em>True</em>: the map may contain only attribute listed in <em>neededAttributes</em> and <em>optionalAttributes</em>
    @param optionalAttributes: a blank delimited list of attribute definitions optional in the Json object.
        The syntax is like that in <em>neededAttributes</em>
    '''
    msg = checkJsonMap(JsonTree, neededAttributes, strict, optionalAttributes)
    if msg is not None:
        raise ValueError(f'Json format error: {msg}')

def checkJsonPath(jsonTree, path: str, nodeType: str):
    '''Checks whether a path in the Json tree exists.
    @param JsonTree: the Json tree node to inspect
    @param path: a blank delimited list of attribute names. Example "person name firstName"
    @param nodeType: the type of the last node:
        Type: s: string i: integer f: floating number F: floating number list m: json object (map) a: json object (array)
    ''' 
    rc = None
    keys = path.split(' ')
    chain = ''
    current = jsonTree
    error = False
    for key in keys:
        if key.startswith('['):
            index = int(key[1:-1])
            if not (type(current) is list):
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
    msg = checkJsonPath(jsonTree, path, nodeType)
    if msg is not None:
        if not mayBeAbsent:
            raise ValueError(f'Json tree problem: {msg}')
        else:
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
    if rc == None:
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
    if rc == None:
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
    if rc == None:
        rc = defaultValue
    return rc

def printableJsonNode(node) -> str:
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

