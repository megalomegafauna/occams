"""
Specification of services provided by this plug-in.

This system employs a database framework known as
`Entity-Attribute-Value with Schema-Relationships Models` or simply `EAV`_ for
short.

.. _EAV: http://www.ncbi.nlm.nih.gov/pmc/articles/PMC61391/
"""

import zope.interface
import zope.schema
from zope.schema.interfaces import IVocabulary
from zope.schema.vocabulary import SimpleVocabulary
from zope.schema.vocabulary import SimpleTerm

from avrc.data.store import MessageFactory as _


# Fixed type vocabulary
typesVocabulary = SimpleVocabulary([
        SimpleTerm(value=zope.schema.Bool, token='boolean', title='Boolean'),
        SimpleTerm(value=zope.schema.Decimal, token='decimal', title='Decimal'),
        SimpleTerm(value=zope.schema.Int, token='integer', title='Integer'),
        SimpleTerm(value=zope.schema.Date, token='date', title='Date'),
        SimpleTerm(value=zope.schema.Datetime, token='datetime', title='Datetime'),
        SimpleTerm(value=zope.schema.TextLine, token='string', title='String'),
        SimpleTerm(value=zope.schema.Text, token='text', title='Text'),
        SimpleTerm(value=zope.schema.Object, token='object', title='Object'),
    ],
    IVocabulary
    )


class DataStoreError(Exception):
    """
    Base class for data store-related errors
    """


class SchemaError(DataStoreError):
    """
    Base class for schema-related errors
    """


class FieldError(SchemaError):
    """
    Base class for field-related errors
    """


class EntityError(DataStoreError):
    """ Base class for entity-related errors
    """


class PropertyError(EntityError):
    """
    Base class for property-related errors (value)
    """

class NotCompatibleError(SchemaError):
    """
    The schema doesn't subclass ``avrc.data.store.directives.Schema``
    """


class MultipleBasesError(SchemaError):
    """ The schema has multiple base classes
    """


class TypeNotSupportedError(FieldError):
    """
    The type specified for a field is not part of the vocabulary of
    supported types.
    """


class ChoiceTypeNotSpecifiedError(FieldError):
    """
    The type specified for the choiced field is unsupported.
    """


class PropertyNotDefinedError(PropertyError):
    """
    An entity's schema does not have the property specified.
    """


class InvalidObjectError(EntityError):
    """
    An object does not provide `IInstance`
    """




class IDataStoreComponent(zope.interface.Interface):
    """
    Marker interface for components of this package.
    """


class IEntry(IDataStoreComponent):
    """
    An object that can be stored in a database.
    """

    id = zope.schema.Int(
        title=_(u'Database ID'),
        description=_(
            u'This value is auto-generated by the database and assigned to '
            u'the item. It should not be modified, otherwise risking '
            u'altered database behavior.'
            ),
        readonly=True
        )


class IDescribeable(IDataStoreComponent):
    """
    A human-readable object.
    """

    name = zope.schema.BytesLine(
        title=_(u'Internal name.'),
        description=_(
            u'This value is usually an ASCII label to be used for '
            u'easy reference of the item. When naming an item, lowercase '
            u'alphanumeric characters or hyphens. The name should also be '
            u'unique within a container.'
            )
        )

    title = zope.schema.TextLine(
        title=_(u'Human readable name'),
        )

    description = zope.schema.Text(
        title=_(u'Description/Prompt')
        )


class IModifiable(IDataStoreComponent):
    """
    An object with modification metadata.
    """

    create_date = zope.schema.Datetime(
        title=_(u'Date Created'),
        readonly=True,
        )

    modify_date = zope.schema.Datetime(
        title=_(u'Date Modified'),
        readonly=True,
        )

    remove_date = zope.schema.Datetime(
        title=_(u'Date Removed'),
        readonly=True,
        required=False,
        )


class IDataBaseItem(IEntry, IDescribeable, IModifiable):
    """
    An object that originates from database.
    """


class IHistoryItem(IDataBaseItem):
    """
    An extension of a database item. Entries of this type are non-unique
    (i.e. the `name` is non-unique) and so a new entry is committed to the
    database for each modification of the object, unless otherwise specified
    by management-utility parameters. When this occurs, the previous
    named entry is decommissioned and a new entry is created.
    Thus, each `create_date` and `remove_date` pair now denotes a point in
    time for an entry with `name`.

    Repurposed standard `IDataBaseItem` attributes:
        ``name``
            Internally, the name is the lifespan of the object. This means
            that there will be multiple entries in the database for
            the object with the given name, and so the timestamps
            will be able to indicate it's lifecycle.
        ``create_date``
            The date when the named entry came into existence.
        ``modify_date``
            Used if changes are ammended to and active named entry (as
            opposed expanding the named entry's history).
        ``remove_date``
            The date when the named entry was decommissioned. A value of
            None denotes that the entry is still active.
    """


class ISchema(IHistoryItem):
    """
    An object that describes how an EAV schema is generated.
    Typically, an EAV schema represents a group of attributes that represent
    a meaningful data set. (e.g. contact details, name, test result.)
    Resulting schema objects can then be used to produce forms such as
    Zope-style interfaces.
    """

    sub_schemata = zope.schema.Iterable(
        title=_(u'Sub Schemata'),
        description=_(u'Listing of schemata that subclass the Zope-style interface.'),
        )

    state = zope.schema.Choice(
        title=_(u'Circulation State'),
        values=sorted(['draft', 'pending-review', 'published', 'retired']),
        default='draft',
        )

    storage = zope.schema.Choice(
        title=_(u'Storage method'),
        description=_(
            u'How the generated objects will be stored. Storage methods are: '
            u'eav - individual values are stored in a type-sharded set of tables; '
            u'resource - the object exists in an external service, such as MedLine; '
            u'table - the object is stored in a conventional SQL table;'
            ),
        values=sorted(['resource', 'eav', 'table']),
        default='eav',
        )

    is_association = zope.schema.Bool(
        title=_(u'Is the schema an association?'),
        description=_(
            u'If set and True, the schema is an defines an association for '
            u'multiple schemata.'
            ),
        required=False,
        )

    is_inline = zope.schema.Bool(
        title=_(u'Is the resulting object inline?'),
        description=_(
            u'If set and True, the schema should be rendered inline to other '
            u'container schemata. '
            ),
        required=False,
        )


# Needs to be defined here, because it's type refers to itself.
ISchema.base_schema = zope.schema.Object(
    title=_(u'Base schema'),
    description=_(
        u'A base schema for this schema to extend, thus emulating OO-concepts.'
        ),
    schema=ISchema,
    required=False,
    )


class IAttribute(IHistoryItem):
    """
    An object that describes how an EAV attribute is generated.
    Typically, an attribute is a meaningful property in the class data set.
    (e.g. user.firstname, user.lastname, contact.address, etc..)
    Note that if the attribute's type is an object, an object_class must
    be specified as well as a flag setting whether the object is to be
    rendered inline.
    Resulting attribute objects can then be used to produce forms such as
    Zope-style schema field.
    """

    schema = zope.schema.Object(
        title=_(u'Schema'),
        description=_(u'The schema that this attribute belongs to'),
        schema=ISchema,
        )

    type = zope.schema.Choice(
        title=_(u'Type'),
        values=sorted(typesVocabulary.by_token.keys()),
        )

    choices = zope.schema.Iterable(
        title=_(u'Acceptable answer choices of type IChoice.')
        )

    is_collection = zope.schema.Bool(
        title=_(u'Is the attribute a collection?'),
        default=False,
        )

    is_required = zope.schema.Bool(
        title=_(u'Is the attribute a required field?'),
        default=False,
        )

    object_schema = zope.schema.Object(
        title=_(u'The object\'s schema'),
        description=_(u'Only applies to attributes of type "object". '),
        schema=ISchema,
        required=False
        )

    value_min = zope.schema.Int(
        title=_(u'Minimum value'),
        description=u'Minimum length or value (depending on type)',
        required=False,
        )

    value_max = zope.schema.Int(
        title=_(u'Maximum value'),
        description=u'Maximum length or value (depending on type)',
        required=False
        )

    collection_min = zope.schema.Int(
        title=_(u'Minimum list length'),
        required=False,
        )

    collection_max = zope.schema.Int(
        title=_(u'Maximum list length'),
        required=False
        )

    validator = zope.schema.TextLine(
        title=_(u'Validation regular expressions'),
        description=_(
            u'Use Perl-derivative regular expression to validate the attribute value.'
            ),
        required=False,
        )

    order = zope.schema.Int(
        title=_(u'Display Order')
        )


class IChoice(IDataBaseItem):
    """
    Possible value constraints for an attribute.
    Note objects of this type are not versioned, as they are merely an
    extension of the IAttribute objects. So if the choice constraints
    are to be modified, a new version of the IAttribute object
    should be created.
    """

    attribute = zope.schema.Object(
        title=_(u'Attribute'),
        description=_(u'The attribute that will be constrained.'),
        schema=IAttribute
        )

    value = zope.schema.TextLine(
        title=_(u'Value'),
        description=_(u'The value will be coerced when stored.')
        )

    order = zope.schema.Int(
        title=_(u'Display Order')
        )


class IEntity(IHistoryItem):
    """
    An object that describes how an EAV object is generated.
    Note that work flow states may be assigned to class entities.
    """

    schema = zope.schema.Object(
        title=_(u'Object Schema'),
        description=_(u'The scheme the object will provide once generated.'),
        schema=ISchema
        )

    state = zope.schema.Choice(
        title=_(u'The current workflow state'),
        values=sorted(['pending-entry', 'pending-review', 'completed', 'not-done']),
        default='pending-entry',
        )

    collect_date = zope.schema.Date(
        title=_(u'Date Collected'),
        description=_(u'The date that the information was physically collected'),
        )


class IValue(IHistoryItem):
    """
    An object that records values assigned to an EAV Entity.
    """

    entity = zope.schema.Object(
        title=_(u'Entity'),
        schema=IEntity
        )

    attribute = zope.schema.Object(
        title=_(u'Property'),
        schema=IAttribute
        )

    choice = zope.schema.Object(
        title=_('Choice'),
        description=_(
            u'Used for book keeping purposes as to where the value was '
            u'assigned from.'
            ),
        schema=IChoice,
        required=False
        )

    value = zope.schema.Field(
        title=_(u'Assigned Value'),
        )




class IInstance(IDataStoreComponent):
    """
    An object derived from EAV entries. Objects of this type are effectively
    stripped from their database references and are simply Python objects.
    """

    __id__ = zope.interface.Attribute(_(
        u'The INTERNAL id of the instance. Tampering or accessing this id '
        u'outside of this package is highly not recommended'))


    __schema__ = zope.interface.Attribute(_(
        u'The schema the created object will represent'
        ))


    __state__ = zope.interface.Attribute(_(
        u'The workflow state of the created object.'
        ))


    title = zope.interface.Attribute(_(
        u'The instance\'s database-unique name'
        ))


    description = zope.interface.Attribute(_(
        u'A description for the object'
        ))


    def setState(state):
        """
        """


    def getState():
        """
        """



class IManager(IDataStoreComponent):
    """
    Specification for management components, that is, components that are in
    charge of a particular class of data. Note that a manager is simply a
    utility into to the data store, therefore creating multiple instances
    of a manager should have no effect on the objects being managed as they
    are still being pulled from the same source.

    Note that ``on`` and ``ever`` arguments are mutually exclusive for
    methods taking them as parameters.
    """


    def keys(on=None, ever=False):
        """
        Generates a collection of the keys for the objects the component is
        managing.

        Arguments
            ``on``
                (Optional) Only checks data active "on" the time specified.
            ``ever``
                (Optional) If set, covers all items "ever" active.

        Returns
            A listing of the object keys being managed by this manager.
        """

    def lifecycles(key):
        """
        Generates the available versions for key.

        Arguments
            ``key``
                The name of the item.

        Returns
            A list of tuples (create, remove) of the specified key
        """


    def has(key, on=None, ever=False):
        """
        Checks if the component is managing the item.

        Arguments
            ``key``
                The name of the item.
            ``on``
                (Optional) Only checks data active "on" the time specified.
            ``ever``
                (Optional) If set, covers all items "ever" active.

        Returns
            True if the manager is in control of the item.
        """


    def purge(key, on=None, ever=False):
        """
        Completely removes the target and all data associated with it
        from the data store.

        Arguments
            ``key``
                The name of the item.
            ``on``
                (Optional) Only checks data active "on" the time specified.
            ``ever``
                (Optional) If set, covers all items "ever" active.

        Returns
            The number of items purged from the data store. (This does
            not include all related items).
        """


    def retire(key):
        """
        Retires the contained item. This means that it's information
        remains, only it's not visible anymore. The reason this
        functionality is useful is so that data can be 'brought back'
        if expiring caused undesired side-effects. Note that this
        method only works with currently active items.

        Arguments
            ``key``
                The name of the item.

        Returns
            True if successfully retired.
        """


    def restore(key):
        """
        Restores a previously retired item. Only works on the most recently
        retired item.

        Arguments
            ``key``
                The name of the item.

        Returns
            The restored object, None otherwise (nothing to restore). In
            cases where the item being restored is still active, the item
            will still be returned, unmodified.
        """


    def get(key, on=None):
        """
        Retrieve an item in the manager.

        Arguments
            ``key``
                The name of the item.
            ``on``
                (Optional) Only checks data active "on" the time specified.

        Returns
            An object maintained by the manger. None if not found.
        """


    def put(key, item):
        """
        Adds the item to the manager. If there is already an item with
        the same name, then the already existing item is retired and
        the new item is added as the currently active item for the name.


        Arguments
            ``key``
                The name of the item.
            ``item``
                The item to be stored in the manager.

        Returns
            A key to the newly stored item
        """


class ISchemaManager(IManager):
    """
    Marker interface for utilities that manage schemata metadata.
    """


class IFieldManager(IManager):
    """
    Marker interface for utilities that manage field metadata.
    """


class IEntityManager(IManager):
    """
    Marker interface for utilities that manage entity metadata.
    """


class IValueManager(IManager):
    """
    Marker interface for utilities that manage value metadata.
    """


class ISchemaManagerFactory(IDataStoreComponent):
    """
    Produces a manager that is able to use database schema descriptions
    to produce Zope-style Interfaces/Schemata.
    """

    def __call__(session):
        """
        Manager call signature.

        Arguments
            ``session``
                A database session to use for retrieval of entry information.
        """


class IFieldManagerFactory(IDataStoreComponent):
    """
    Produces a manager that is able to use database attribute descriptions
    to produce Zope-style Fields.
    """

    def __call__(schema):
        """
        Manager call signature.

        Arguments
            ``schema``
                An object that provides `ISchema`, to know which fields
                to retrieve.
        """


class IEntityManagerFactory(IDataStoreComponent):
    """
    Produces a manager that is able to use database entry descriptions
    to produce an object that provides a Zope-style interface that is
    also stored in the database.
    """

    def __call__(session):
        """
        Manager call signature.

        Arguments
            ``session``
                A database session to use for retrieval of entry information.
        """


class IValueManagerFactory(IDataStoreComponent):
    """
    Produces a manager that is able to use database value descriptions to
    produce the values assigned to an object.
    """

    def __call__(entity):
        """
        Manager call signature.

        Arguments
            ``entity``
                An object that provides `IEntity`, to know which assignments
                to retrieve.
        """


class IHierarchy(IDataStoreComponent):
    """
    Offers functionality on inspecting a the hierarchy of a schema
    description.
    """

    def getChildren(key, on=None):
        """
        Return the Zope-style interfaces of all the children (leaf nodes)
        in the hierarchy of the specified name.

        Arguments
            ``key``
                The name of the parent schema.
            ``on``
                (Optional) Only checks data active "on" the time specified.
        """


    def getChildrenNames(key, on=None):
        """
        Return the names of all the children (leaf nodes)
        in the hierarchy of the specified name.

        Arguments
            ``key``
                The name of the parent schema.
            ``on``
                (Optional) Only checks data active "on" the time specified.
        """

class IHierarchyFactory(IDataStoreComponent):
    """
    Produces an object that is able to inspect the hierarchy of schemata.
    """

    def __call__(session):
        """
        Produces a hierarchy inspector.

        Arguments
            ``session``
                A database session to use for retrieval of entry information.
        """


class IDataStore(IDataStoreComponent):
    """
    Represents a data store utility that can be added to a site. It is in
    charge of managing the entire network of data that will be created from
    schemata, etc. It achieves this by using registered helper utilities
    that it adapts into called 'managers'.
    """


class IDatastore(zope.interface.Interface):
    """
    Legacy DataStore specification.
    Deprecated in favor of ``IDataStore``
    """


class IDataStoreFactory(IDataStoreComponent):
    """
    How to instantiate a DataStore
    """

    def __call__(session):
        """ The session to use.
        """

class IDataStoreExtension(IDataStoreComponent):
    """
    A factory specification for legacy systems that still depend on a
    DataStore object as a utility.
    """

    def __call__(datastore):
        """
        The ``DataStore`` to use.
        """


class ISchemaFormat(IDataStoreComponent):
    """
    """
