
import datetime
import unittest2 as unittest

from zope.interface.interface import InterfaceClass
import zope.schema
from zope.schema.interfaces import WrongType

from occams.datastore import directives
from occams.datastore import model


class SchemaOrFieldDirectivesTestCase(unittest.TestCase):
    """
    Verifies directive library
    """

    def test_id (self):
        iface = InterfaceClass('Sample')
        field = zope.schema.Text(__name__='foo', title=u'')
        directive = directives.__id__
        with self.assertRaises(WrongType):
            directive.set(iface, 'This is an id')
        with self.assertRaises(WrongType):
            directive.set(iface, 12.4)

        value = 1234
        directive.set(iface, value)
        self.assertEqual(value, directive.bind().get(iface))
        directive.set(field, value)
        self.assertEqual(value, directive.bind().get(field))

    def test_version (self):
        iface = InterfaceClass('Sample')
        field = zope.schema.Text(__name__='foo', title=u'')
        directive = directives.version
        with self.assertRaises(WrongType):
            directive.set(iface, 'This is an id')
        with self.assertRaises(WrongType):
            directive.set(iface, 12.4)
        with self.assertRaises(WrongType):
            directive.set(iface, 1234)

        # Only accepts dates (not datetime values)
        with self.assertRaises(WrongType):
            value = datetime.datetime.now()
            directive.set(iface, value)

        value = datetime.date.today()
        directive.set(iface, value)
        self.assertEqual(value, directive.bind().get(iface))
        directive.set(field, value)
        self.assertEqual(value, directive.bind().get(field))

    def test_inline (self):
        iface = InterfaceClass('Sample')
        field = zope.schema.Text(__name__='foo', title=u'')
        directive = directives.inline
        with self.assertRaises(WrongType):
            directive.set(iface, 'This is an id')
        with self.assertRaises(WrongType):
            directive.set(iface, 12.4)

        value = True
        directive.set(iface, value)
        self.assertEqual(value, directive.bind().get(iface))
        directive.set(field, value)
        self.assertEqual(value, directive.bind().get(field))


class SchemaDirectivesTestCase(unittest.TestCase):

    def test_title(self):
        iface = InterfaceClass('Sample')
        directive = directives.title
        with self.assertRaises(WrongType):
            directive.set(iface, 1234)
        with self.assertRaises(WrongType):
            directive.set(iface, 'This is \n a title')

        value = u'This is a title'
        directive.set(iface, value)
        self.assertEqual(value, directive.bind().get(iface))

    def test_description(self):
        iface = InterfaceClass('Sample')
        directive = directives.description
        self.assertRaises(WrongType, directive.set, iface, 1234)

        value = u'This is a title'
        directive.set(iface, value)
        self.assertEqual(value, directive.bind().get(iface))


class FieldDirectivesTestCase(unittest.TestCase):

    def test_type (self):
        field = zope.schema.Choice(__name__='foo', title=u'', values=[1, 2, 3])
        directive = directives.type

        # Check all supported
        for type_ in model.Attribute.__table__.c.type.type.enums:
            directive.set(field, type_)

        value = 'string'
        directive.set(field, value)
        self.assertEqual(value, directive.bind().get(field))
