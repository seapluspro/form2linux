'''
JsonUtilsTest.py

Created on: 20.08.2023
    Author: SeaPlusPro
   License: CC0 1.0 Universal
'''
import unittest
import json
from text.JsonUtils import checkJsonMap, checkJsonNodeType, checkJsonPath, \
    printableJsonNode, nodeOfJsonTree, optionalBoolNode, optionalFloatNode


def inDebug(): return False


class JsonUtilsTest(unittest.TestCase):

    def testString(self):
        if inDebug():
            return
        obj = json.loads('{"id": "adam", "name": "adam smith"}')
        obj2 = json.loads('{"id": 3, "name": [0, 3]}')
        obj3 = json.loads('{"id": null, "name": {"x": 3}}')

        self.assertEqual(None, checkJsonMap(obj, "id:s name:s"))
        self.assertEqual('''3 is not a string
[..] is not a string''', checkJsonMap(obj2, "id:s name:s"))
        self.assertEqual('<None> is not a string\n{..} is not a string',
                         checkJsonMap(obj3, "id:s name:s"))

    def testNumber(self):
        if inDebug():
            return
        obj = json.loads('{"id": 123, "length": 14.5, "size": 1E-2}')
        obj2 = json.loads('{"id": "john", "length": [0, 3], "size": {"a": 1}}')

        self.assertEqual(None, checkJsonMap(obj, "id:i length:f size:f"))
        self.assertEqual("missing attribute(s): name Size",
                         checkJsonMap(obj, "name:i length:f Size:f"))
        self.assertEqual('''"john" is not an integer
[..] is not a float
{..} is not a float''', checkJsonMap(obj2, "id:i length:f size:f"))

    def testComplex(self):
        if inDebug():
            return
        obj = json.loads('{"list": ["a", "b"], "map": {"a": 1}}')
        obj2 = json.loads('{"list": "wrong", "map": 3}')
        obj3 = json.loads('{"list": {"a": 3}, "map": [3]}')

        self.assertEqual(None, checkJsonMap(obj, "list:a map:m"))
        error = checkJsonMap(obj2, "list:a map:m")
        self.assertEqual('"wrong" is not a list\n3 is not a map', error)
        self.assertEqual('{..} is not a list\n[..] is not a map',
                         checkJsonMap(obj3, "list:a map:m"))

    def testOptional(self):
        if inDebug():
            return
        obj = json.loads('{"id": "adam", "name": "adam smith"}')
        self.assertEqual(None, checkJsonMap(obj, None, True, "id:s name:s"))
        self.assertEqual('''"adam" is not an integer\n"adam smith" is not a float''',
                         checkJsonMap(obj, None, True, "id:i name:f"))

    def testStrict(self):
        if inDebug():
            return
        obj = json.loads('{"id": "adam", "name": "adam smith", "no": 3}')
        obj2 = json.loads('{"id": "adam", "number": 3}')
        self.assertEqual('''unknown attribute: no''',
                         checkJsonMap(obj, "id:s", True, "name:s"))
        self.assertEqual('''unknown attribute: number''',
                         checkJsonMap(obj2, "id:s", True, "name:s"))

    def testNodeTypeOK(self):
        if inDebug():
            return
        obj = json.loads(
            '{"int": 123, "name": "Jonny", "float": 0.2, "bool": true, "list":[1], "object": {"a":"b"}}')
        self.assertEqual(None, checkJsonNodeType('i', obj['int']))
        self.assertEqual(None, checkJsonNodeType('s', obj['name']))
        self.assertEqual(None, checkJsonNodeType('f', obj['float']))
        self.assertEqual(None, checkJsonNodeType('b', obj['bool']))
        self.assertEqual(None, checkJsonNodeType('a', obj['list']))
        self.assertEqual(None, checkJsonNodeType('m', obj['object']))

    def testNodeTypeError(self):
        if inDebug():
            return
        obj = json.loads(
            '{"int": 123, "name": "Hugo", "float": 0.2, "bool": true, "list":[1], "object": {"a":"b"}}')
        self.assertEqual('123 is not a string',
                         checkJsonNodeType('s', obj['int']))
        self.assertEqual('"Hugo" is not an integer',
                         checkJsonNodeType('i', obj['name']))
        self.assertEqual('0.2 is not a boolean',
                         checkJsonNodeType('b', obj['float']))
        self.assertEqual('True is not a float',
                         checkJsonNodeType('f', obj['bool']))
        self.assertEqual('[..] is not a map',
                         checkJsonNodeType('m', obj['list']))
        self.assertEqual('{..} is not a list',
                         checkJsonNodeType('a', obj['object']))

    def testPathOK(self):
        if inDebug():
            return
        obj = json.loads(
            '{"person": {"name": {"first":"Huber", "last": "Joe"}}}')
        self.assertEqual(None, checkJsonPath(obj, 'person name first', 's'))

    def testPathTypeError(self):
        if inDebug():
            return
        obj = json.loads(
            '{"person": {"name": {"first":"Huber", "last": "Joe"}}}')
        self.assertEqual('"Huber" is not an integer',
                         checkJsonPath(obj, 'person name first', 'i'))

    def testPathNodeError(self):
        if inDebug():
            return
        obj = json.loads(
            '{"person": {"name": {"first":"Huber", "last": "Joe"}}}')
        self.assertEqual('missing Json node "firstname" in person.name', checkJsonPath(
            obj, 'person name firstname', 'i'))

    def testPrintableJsonNode(self):
        if inDebug():
            return
        obj = json.loads(
            '{"int": 123, "name": "Hugo", "float": 0.2, "bool": true, "list":[1], "None": null, "object": {"a":"b"}}')
        self.assertEqual('123', printableJsonNode(obj['int']))
        self.assertEqual('"Hugo"', printableJsonNode(obj['name']))
        self.assertEqual('0.2', printableJsonNode(obj['float']))
        self.assertEqual('True', printableJsonNode(obj['bool']))
        self.assertEqual('[..]', printableJsonNode(obj['list']))
        self.assertEqual('{..}', printableJsonNode(obj['object']))
        self.assertEqual('<None>', printableJsonNode(obj['None']))

    def testNodeOfJsonTree(self):
        if inDebug():
            return
        obj = json.loads(
            '{"person": {"name": {"first":"Huber", "last": "Joe"}}}')
        self.assertEqual('Joe', nodeOfJsonTree(obj, 'person name last', 's'))

    def testOptionalBoolNode(self):
        if inDebug():
            return
        obj = json.loads(
            '{"person": {"params": {"true":true, "false":false}}}')
        self.assertEqual(True, optionalBoolNode(obj, 'person params true'))
        self.assertEqual(False, optionalBoolNode(obj, 'person params false'))
        self.assertEqual(False, optionalBoolNode(obj, 'person params unknown'))
        self.assertEqual(True, optionalBoolNode(
            obj, 'person params unknown', True))

    def testOptionalFloatNode(self):
        if inDebug():
            return
        obj = json.loads('{"person": {"params": {"p1": 4.9}}}')
        self.assertEqual(4.9, optionalFloatNode(obj, 'person params p1'))
        self.assertEqual(None, optionalFloatNode(obj, 'person params unknown'))
        self.assertEqual(-1.2, optionalFloatNode(obj, 'person unknown', -1.2))
