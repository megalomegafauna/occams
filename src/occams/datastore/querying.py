u"""
A utility for allowing the access of entered schema data to be represented
in a SQL table-like fashion.

Splitting algorithms are as follows:
    **NAME**
        No splitting should occur, all attributes are grouped by their name
    **CHECKSUM**
        All attributes are grouped by their checksum
    **ID**
        Aggressively split by attribute id

"""

import ordereddict

import sqlalchemy as sa
from sqlalchemy import orm

from occams.datastore import model as datastore
from occams.datastore.model import storage


def schemaToQueryById(session, schema_name):
    u"""
    Builds a sub-query for a schema using the ID split algorithm
    """
    header = getHeaderById(session, schema_name)
    query = buildQuery(session, schema_name, header)
    return header, query


def schemaToQueryByName(session, schema_name):
    u"""
    Builds a sub-query for a schema using the NAME split algorithm
    """
    header = getHeaderByName(session, schema_name)
    query = buildQuery(session, schema_name, header)
    return header, query


def schemaToQueryByChecksum(session, schema_name):
    u"""
    Builds a sub-query for a schema using the CHECKSUM split algorithm
    """
    header = getHeaderByChecksum(session, schema_name)
    query = buildQuery(session, schema_name, header)
    return header, query


def buildQuery(session, schema_name, header):
    u"""
    Builds a schema entity data report table as an aliased sub-query.

    Suggested usage of subquery is via "common table expressions" (i.e. WITH statement...)

    Arguments
        ``session``
            The database session to use
        ``name``
            The schema to use for building the sub-query
        ``header``
            The column plan tha will be used for aligning the data

    Returns
        A SQLAlchemy aliased sub-query.

        Developer note: the results that will be returned by the subquery are
        named tuples of each result using the names of the naming schema as the
        property names.
    """

    entity_query = (
        session.query(datastore.Entity.id.label(u'entity_id'))
        .join(datastore.Entity.schema)
        .filter(datastore.Schema.name == schema_name)
        .filter(datastore.Schema.publish_date != None)
        )

    for path, attributes in header.iteritems():
        column_name = u'_'.join(path)
        type_name = attributes[-1].type
        attribute_ids = [a.id for a in attributes]
        value_source = storage.nameModelMap[type_name]
        value_name = u'%s_%s' % (column_name, type_name)
        value_class = orm.aliased(value_source, name=value_name)
        value_clause = (
            (value_class.entity_id == datastore.Entity.id)
            & (value_class.attribute_id.in_(attribute_ids))
            )
        # sqlalchemy doesn't like the hybrid property for casting
        value_column = value_class._value
        or_ = lambda x, y: x or y
        is_ever_collection = reduce(or_, [a.is_collection for a in attributes])
        is_sqlite = u'sqlite' in str(session.bind.url)
        is_postgres = u'postgres' in str(session.bind.url)

        # very special case for sqlite as it has limited data type
        if is_sqlite and type_name == u'date':
            value_casted = sa.func.date(value_column)
        elif is_sqlite and type_name == u'datetime':
            value_casted = sa.func.datetime(value_column)
        else:
            value_casted = sa.cast(value_column, storage.nameCastMap[type_name])

        if is_ever_collection:
            # collections are built using correlated subqueries
            if is_postgres:
                # use postgres arrays if available
                aggregator = sa.func.array
                aggregate_values = value_casted
            else:
                # everything else get's a comma-delimeted string
                aggregator = lambda q: q
                aggregate_values = sa.func.group_concat(value_casted)

            column = aggregator(
                session.query(aggregate_values)
                .filter(value_clause)
                .correlate(datastore.Entity)
                .subquery()
                )
        else:
            # scalars are build via LEFT JOIN
            entity_query = entity_query.outerjoin(value_class, value_clause)
            column = value_casted

        entity_query = entity_query.add_column(column.label(column_name))

    query = entity_query.subquery(schema_name)
    return query


def getHeaderByName(session, schema_name, path=()):
    u"""
    """
    plan = ordereddict.OrderedDict()
    attribute_query = getAttributeQuery(session, schema_name)
    for attribute in attribute_query:
        if attribute.type == u'object':
            sub_name = attribute.object_schema.name
            sub_path = (attribute.name,)
            sub_plan = getHeaderByName(session, sub_name, sub_path)
            plan.update(sub_plan)
        else:
            column_path = path + (attribute.name,)
            plan.setdefault(column_path, []).append(attribute)
    return plan


def getHeaderByChecksum(session, schema_name, path=()):
    u"""
    """
    plan = ordereddict.OrderedDict()
    attribute_query = getAttributeQuery(session, schema_name)
    for attribute in attribute_query:
        if attribute.type == u'object':
            sub_name = attribute.object_schema.name
            sub_path = (attribute.name,)
            sub_plan = getHeaderByChecksum(session, sub_name, sub_path)
            plan.update(sub_plan)
        else:
            column_path = path + (attribute.name, attribute.checksum)
            plan.setdefault(column_path, []).append(attribute)
    return plan


def getHeaderById(session, schema_name, path=()):
    u"""
    Builds a column header for the schema hierarchy using the ID algorithm.
    The header columns reported are only the basic data types.

    Note that the final columns are ordered by most recent order number within
    the parent, then by the parent's publication date (oldest to newest).

    Arguments
        ``session``
            The session to query plan from
        ``name``
            The name of the schema to get columns plans for
        ``path``
            (Optional)  current traversing path in the hierarchy.
            This is useful if you want to prepend additional column
            prefixes.

    Returns
        An ordered dictionary using the path to the attribute as the key,
        and the associated attribute list as the value. The path will
        also contain the attribute's id.
    """
    plan = ordereddict.OrderedDict()
    attribute_query = getAttributeQuery(session, schema_name)
    for attribute in attribute_query:
        if attribute.type == u'object':
            sub_name = attribute.object_schema.name
            sub_path = (attribute.name,)
            sub_plan = getHeaderById(session, sub_name, sub_path)
            plan.update(sub_plan)
        else:
            column_path = path + (attribute.name, attribute.id)
            plan.setdefault(column_path, []).append(attribute)
    return plan


def getAttributeQuery(session, schema_name):
    u"""
    Builds a subquery for the all attributes ever contained in the schema.
    This does not include sub-attributes.

    Arguments:
        ``session``
            The SQLAlchemy session to use
        ``schema_name``
            The schema to search for in the session

    Returns:
        A subquery for all the attributes every contained in the schema.
        Attribute lineages are are ordered by their most recent position in the
        schema, then by oldest to newest within the lineage.
    """

    # aliased so we don't get naming ambiguity
    RecentAttribute = orm.aliased(datastore.Attribute, name=u'recent_attribute')

    # build a subquery that determines an attribute's most recent order
    recent_order_subquery = (
        session.query(RecentAttribute.order)
        .join(RecentAttribute.schema)
        .filter(datastore.Schema.name == schema_name)
        .filter(datastore.Schema.publish_date != None)
        .filter(RecentAttribute.name == datastore.Attribute.name)
        .order_by(datastore.Schema.publish_date.desc())
        .limit(1)
        .correlate(datastore.Attribute)
        .as_scalar()
        )

    attribute_query = (
        session.query(datastore.Attribute)
        .options(
            orm.joinedload(datastore.Attribute.schema),
            orm.joinedload(datastore.Attribute.choices),
            )
        .join(datastore.Attribute.schema)
        .filter(datastore.Schema.name == schema_name)
        .filter(datastore.Schema.publish_date != None)
        .order_by(
            # lineage order
            recent_order_subquery.asc(),
            # oldest to newest within the lineage
            datastore.Schema.publish_date.asc(),
            )
        )

    return attribute_query

