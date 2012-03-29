#!/usr/bin/env python
"""Upgrade process for EAV versioning cleanup.

#########1#########2#########3#########4#########5#########6#########7#####

Precondition Assumptions:
    1. There are two databases per run (eg avrc_demo_data and avrc_data)
    2. The avrc_data will start as a straight up copy of avrc_demo_data.
    3. For avrc_data we have "DROP TABLE"-ed: entity, state, datetime, 
        integer, object, decimal, string, schema, attribute, and choice.
    4. During the upgrade process, the website will be turned off.
    5. The source schema table is unique on (schema.name,DATE(create_date))

Design Assumptions:
    1. Reflect avrc_demo_data w/ sqlsoup (readonly to ensure no changes).
    2. No modifications to support tables (specimen, subject, etc) will be necessary.
    3. Remove dates will respect chronology (ie data processed in order leaves final row with NULL remove date, and the rest "clean").
    4. The process will run in one go, within a single night or weekend.

"""
from sqlalchemy.ext.sqlsoup import SqlSoup
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy import create_engine
from occams.datastore import model

from sqlalchemy import func
from sqlalchemy import String
from sqlalchemy import Date
from sqlalchemy.sql.expression import case
from sqlalchemy.sql.expression import cast
from sqlalchemy.sql.expression import null
from sqlalchemy.sql.expression import literal_column
from sqlalchemy.orm import aliased

global Session
Session = scoped_session(
    sessionmaker(
        class_=model.DataStoreSession,
        user=(lambda : "bitcore@ucsd.edu") # can be called by a library
        ))

global old_model

def main():
    """Handle argv, specialize globals, launch job."""
    import sys
    usage = """overhaul.py OLDCONNECT NEWCONNECT"""
    configureGlobalSession(sys.argv[1], sys.argv[2])
    addUser("bitcore@ucsd.edu")
    moveInAllSchemas()

    #moveInAttributesAndChoices() # as part of the schemas?

    # Do some QA before implementing the last two move-ins
    # because it would suck to have something wrong and have
    # to re-work entities...
    moveInEntities()
    moveInValues() # as part of the entities?

    Session.commit()
    if isWorking():
        print "Yay!"

def moveInEntities():
    pass

def moveInValues():
    pass

def moveInAttributesAndChoices():
    schemaChanges = getKnownSchemaChanges()
    for revision in schemaChanges:
        o_attr = getOriginalAttrsAndChoices()
        createAttrs(revision,o_attrs)

def moveInAllSchemas():
    schemaChanges = getKnownSchemaChanges()
    for revision in schemaChanges:
        # PARENTS SCHEMAS
        p_original = getOriginalParentSchema(revision)
        new_parent = createSchema(revision,p_original)
        # CHILD SCHEMAS AND THEIR PARENT ATTRIBUTES
        c_originals = getOriginalChildSchemas(p_original)
        for c_original in c_originals:
            new_child = createSchema(revision,c_original)
            p_attr = getLinkingAttr(c_original)
            new_attrs = createAttr(revision,new_parent,new_child,p_attr)

            # Do attribute/choice move-in here or as separate step
            # in main()?  That's the first decision :-)

        print "Installed",len(c_originals),"child schemas!"

def createAttr(revision,new_parent,new_child,p_attr):
    """Given a schema name and revision date, create such a schema"""
    form_name, publish_date = revision[0],revision[1]
    simples = [
            "name","title","description",
            "type","is_collection","is_required","order",
            "create_date","modify_date"]
    buildIt = {
        # the "_id" will be added to the keys and the ".id" on the
        # instances will be handled by convention-respecting machinery
        # in model.Attribute when (**builtIt) is processed.
        "schema":new_parent,
        "object_schema":new_child,
        }
    for simple in simples:
        buildIt[simple] = getattr(p_attr,simple)
    toEnter = model.Attribute(**buildIt)
    Session.add(toEnter)
    Session.flush()
    print "Added an attribute named",p_attr.name

def createSchema(revision,original):
    """Given a schema name and revision date, create such a schema"""
    form_name, publish_date = revision[0],revision[1]
    simples = ["name","title","description","storage","create_date","modify_date"]
    buildIt = {
        "state":"published",
        "publish_date":publish_date,
        }
    for simple in simples:
        buildIt[simple] = getattr(original,simple)
    toEnter = model.Schema(**buildIt)
    Session.add(toEnter)
    Session.flush()
    print "Added a schema for",revision
    return toEnter

def getLinkingAttr(c_original):
    """Get original parent attribute given original child schema"""
    sch = old_model.entity("schema")
    att = old_model.entity("attribute")
    qry = (
        Session.query(att)
        .filter(att.object_schema_id == c_original.id)
        )
    return qry.one()

def getOriginalChildSchemas(parent_schema):
    """Return all "original" child schemas for a given parent."""
    # NOTE: We know that child schemas were never really versioned
    # at the schema level.  Weird attributes, but that's it.
    sch = old_model.entity("schema")
    att = old_model.entity("attribute")
    qry = (
        Session.query(sch)
        .join(att,(sch.id == att.object_schema_id))
        .filter(att.schema_id == parent_schema.id)
        )
    return qry.all()

def getOriginalParentSchema(revision):
    """Return... Track down the template Yay!"""
    import sqlalchemy.exc
    form_name, publish_date = revision[0],revision[1]
    sch = old_model.entity("schema")
    qry = (
        Session.query(sch)
        .filter(sch.name == form_name)
        .filter(cast(sch.create_date,Date) <= publish_date)
        .filter((cast(sch.remove_date,Date) > publish_date) | (sch.remove_date == None))
        )
    try:
        out = qry.one()
    except sqlalchemy.exc.SQLAlchemyError as err:
        import pdb;pdb.set_trace()
        print "foo"
    return out

def addUser(email):
    #user = Session.query(model.User).filter(model.User.key == email).first()
    #if not user:
    Session.add(model.User(key=email))
    Session.flush()

#def makeSchema(blob):
#    """Not used code yet... conceptual example from Marco"""
#    schema = model.Schema(
#       name='Foo',
#       title='Foo Form',
#       state='published',
#       publish_date=date(),
#       attributes=dict(
#           model.Attribute(name='foo', title=u'Enter Foo', order=0, choices=[
#               model.Choice(),
#               model.Choice(),
#           ]),
#           model.Attribute(name='foo', title=u'Enter Foo', order=1),
#           model.Attribute(name='foo', title=u'Enter Foo', order=2),
#           model.Attribute(name='foo', title=u'Enter Foo', order=3),
#       )
#    Session.add(schema)
#    Session.flush()
#    assert schema.revision == 0
#    schema.description = 'adfasdfadsfasd'
#    Session.flush()
#    assert schema.revision == 1
#    newSchema = copy(schema)
#    session.add(newSchema)


def getKnownSchemaChanges(): 
    from sqlalchemy import func
    global Session
    changes = changeTableFactory(Session)
    subforms = subSchemaNamesTableFactory(Session)
    evilforms = baseSchemaNamesTableFactory(Session)
    realChanges = (
        Session.query(changes.c.schema_name, changes.c.change_date,func.count().label('revisionCount'))
        .filter(changes.c.change_date != None)
        .filter(~changes.c.schema_name.in_(subforms))
        .filter(~changes.c.schema_name.in_(evilforms))
        .group_by(changes.c.schema_name, changes.c.change_date)
        .order_by(changes.c.schema_name, changes.c.change_date)
        )
    return realChanges.all()

def configureGlobalSession(old_connect, new_connect):
    """Set up Session for data manipulation and create new tables as side effect."""
    global old_model
    new_engine = create_engine(new_connect)
    model.Model.metadata.drop_all(bind=new_engine, checkfirst=True)
    model.Model.metadata.create_all(bind=new_engine, checkfirst=True)
    tables = []
    tables_model = model.Model.metadata.sorted_tables
    tables += dict.fromkeys(tables_model, new_engine).items()
    Session.configure(binds=dict(tables))
    old_model = SqlSoup(old_connect,session=Session)



def baseSchemaNamesTableFactory(session):
    """Helper method to generate a SQLAlchemy expression table for base schemata names"""
    BaseSchema = aliased(old_model.entity("schema"), name='_base')
    # A query that builds a base schema name result set
    query = (
        session.query(BaseSchema.name)
        .join((old_model.entity("schema"), (old_model.entity("schema").base_schema_id == BaseSchema.id)))
        .group_by(BaseSchema.name)
        )
    return query.subquery()

def literal(value):
    """Helper method to convert a Python value into a SQL string"""
    return literal_column('\'%s\'' % str(value), String)

def subSchemaNamesTableFactory(session):
    """Helper method to generate a SQLAlchemy expression table for sub schemata names"""
    query = (
        session.query(old_model.entity("schema").name)
        .join((old_model.entity("attribute"), (old_model.entity("attribute").object_schema_id == old_model.entity("schema").id)))
        .group_by(old_model.entity("schema").name)
        )
    return query.subquery()

def changeTableFactory(session):
    """Helper method to generate a SQLAlchemy expression table for schemata changes.
    The result set will include all modifications done to each schema."""
    SubSchema = aliased(old_model.entity("schema"), name='_subschema')
    SubAttribute = aliased(old_model.entity("attribute"), name='_subattribute')

    # A query that builds a revision log result set of all master forms,
    # which also include the revisions of subforms
    query = (
        # Master schema create dates
        session.query(
            old_model.entity("schema").name.label('schema_name'),
            null().label('attribute_name'),
            cast(old_model.entity("schema").create_date,Date).label("change_date"),
            )
        .union(
            # Master schema removal dates
            session.query(
                old_model.entity("schema").name, 
                null(), 
                cast(old_model.entity("schema").remove_date,Date),
                ),
            # Master schema attribute create dates
            session.query(
                old_model.entity("schema").name,
                # Only report non-object values as part of the field count
                case([
                    (old_model.entity("attribute").type != literal('object'),
                        (old_model.entity("schema").name + literal('.') + old_model.entity("attribute").name))
                    ]),
                cast(old_model.entity("attribute").create_date,Date)
                )
            .join((old_model.entity("attribute"), (old_model.entity("attribute").schema_id == old_model.entity("schema").id))),

            # Master schema attribute removal dates
            session.query(
                old_model.entity("schema").name, 
                null(), 
                cast(old_model.entity("attribute").remove_date,Date)
                )
            .join((old_model.entity("attribute"), (old_model.entity("attribute").schema_id == old_model.entity("schema").id))),

            # Sub schema create dates
            session.query(
                old_model.entity("schema").name, 
                null(),
                cast(SubSchema.create_date,Date)
                )
            .join((old_model.entity("attribute"), (old_model.entity("attribute").schema_id == old_model.entity("schema").id)))
            .join((SubSchema, (SubSchema.id == old_model.entity("attribute").object_schema_id))),

            # Sub schema removal dates
            session.query(
                old_model.entity("schema").name, 
                null(), 
                cast(SubSchema.remove_date,Date)
                )
            .join((old_model.entity("attribute"), (old_model.entity("attribute").schema_id == old_model.entity("schema").id)))
            .join((SubSchema, (SubSchema.id == old_model.entity("attribute").object_schema_id))),

            # Sub schema attribute create dates
            session.query(
                old_model.entity("schema").name,
                SubSchema.name + literal('.') + SubAttribute.name,
                cast(SubAttribute.create_date,Date)
                )
            .join((old_model.entity("attribute"), (old_model.entity("attribute").schema_id == old_model.entity("schema").id)))
            .join((SubSchema, (SubSchema.id == old_model.entity("attribute").object_schema_id)))
            .join((SubAttribute, (SubAttribute.schema_id == SubSchema.id))),

            # Sub schema attribute removal dates
            session.query(
                    old_model.entity("schema").name, 
                    null(), 
                    cast(SubAttribute.remove_date,Date)
                    )
            .join((old_model.entity("attribute"), (old_model.entity("attribute").schema_id == old_model.entity("schema").id)))
            .join((SubSchema, (SubSchema.id == old_model.entity("attribute").object_schema_id)))
            .join((SubAttribute, (SubAttribute.schema_id == SubSchema.id))),
            )
        )
    return query.subquery('_change')

def isWorking():
    """Did [] work?"""
    global old_model
    good = True
    #if Session.query(old_model.entity("schema")).count() != 32:
    #    print "Wrong number of schemas added"
    #    good = False
    return good

if __name__ == '__main__':
    main()

