from Globals import PersistentMapping
from StringIO import StringIO
from Acquisition import aq_base
from Products.CMFCore.utils import getToolByName
from Products.Archetypes.Extensions.utils import install_catalog
from Products.Archetypes.Extensions.utils import install_referenceCatalog
from Products.Archetypes.utils import make_uuid
from Products.Archetypes.config import *

def fixArchetypesTool(portal, out):
    at = portal.archetype_tool

    if not hasattr(at, '_templates'):
        #They come in pairs
        at._templates = PersistentMapping()
        at._registeredTemplates = PersistentMapping()

    if not hasattr(at, 'catalog_map'):
        at.catalog_map = PersistentMapping()

    install_catalog(portal, out)


def migrateReferences(portal, out):
    # FIRST
    # a 1.2 -> 1.3 (new annotation style) migration path
    
    at = getToolByName(portal, TOOL_NAME)
    rc = getToolByName(portal, REFERENCE_CATALOG)
    uc = getToolByName(portal, UID_CATALOG)

    # Old 1.2 style references are stored inside archetype_tool on the 'ref'
    # attribute
    refs = getattr(at, 'refs', None)
    if refs:
        count=0
        print >>out, "Old references are stored in %s, so migrating them to new style reference annotations." % (TOOL_NAME)
        allbrains = uc()
        for brain in allbrains:
            sourceObj = brain.getObject()
            sourceUID = getattr(sourceObj.aq_base, olduididx, None)
            if not sourceUID: continue
            # references migration starts
            for targetUID, relationship in refs.get(sourceUID, []):
                # get target object
                targetBrains = uc(olduididx=targetUID)
                targetObj=targetBrains[0].getObject()
                # create new style reference
                rc.addReference(sourceObj, targetObj, relationship)
                count+=1        
        print >>out, "%s old references migrated." % count
        # after all remove the old-style reference attribute
        delattr(at, 'refs')
        return
    
    return
    # :-( XXX THE FOLLOWING ISNT TESTED, just copied from old buggy code !!!
    # maybe theres something useful for code-recycling in
    # --jensens
                
    # SECOND
    # a 1.3.b2 -> 1.3 (new annotation style) migration path
    # We had a reference catalog, make sure its doing annotation
    # based references

    # looks like its a folder with stuff in it.. old style
    # we want to do this quickly so we will grab all the
    # objects for each unique source ID and push them into
    # that source object
    sids = rc.uniqueValuesFor('sourceUID')
    for sid in sids:
        set = rc(sourceUID=sid)
        sourceObject = uc(UID=sid)[0].getObject()
        if not sourceObject: continue
        annotations = sourceObject._getReferenceAnnotations()
        for brain in set:
            # we need to uncatalog the ref at its current path
            # and then stick it on the new object and index it
            # again under its new relative pseudo path
            path = brain.getPath()
            ref = getattr(rc, path, None)
            if ref is None: continue
            if path.find('ref_') != -1:
                rc.uncatalog_object(path)
                uc.uncatalog_object(path)

                # make sure id==uid
                setattr(ref, UUID_ATTR, make_uuid())
                ref.id = ref.UID()
                # now stick this in the annotation
                # unwrap the ref
                ref = aq_base(ref)
                annotations[ref.UID()] = ref
            rc._delOb(path)
        # I might have to do this each time (to deal with an
        # edge case), but I suspect not
        sourceObject._catalogRefs(portal)


    print >>out, "Migrated References"

    #Reindex for new UUIDs
    uc.manage_reindexIndex()
    rc.manage_reindexIndex()

olduididx = 'old_tmp_at_uid'

def migrateUIDs(portal, out):
    count=0
    uc = getToolByName(portal, UID_CATALOG)    
    
    # temporary add a new index    
    if olduididx not in uc.indexes():
        uc.addIndex(olduididx, 'FieldIndex', extra=None)
        if not olduididx in uc.schema():
            uc.addColumn(olduididx)
    
    # clear UID Catalog 
    uc.manage_catalogClear()
    
    # rebuild UIDS on objects and in catalog
    allbrains = portal.portal_catalog()
    for brain in allbrains:
        # get a uid for each thingie
        obj = brain.getObject()
        objUID = getattr(obj.aq_base, '_uid', None)        
        if not objUID: continue    # not an old style AT?
        setattr(obj, olduididx, objUID) # this one can be part of the catalog
        delattr(obj, '_uid')
        setattr(obj, UUID_ATTR, None)
        obj._register()            # creates a new UID
        obj._updateCatalog(portal) # to be sure
        count+=1
    print >>out, count, "UID's migrated."

def removeOldUIDs(portal, out):
    # remove temporary needed index 
    uc = getToolByName(portal, UID_CATALOG)    
    if olduididx in uc.indexes():
        uc.delIndex(olduididx)
        if olduididx in uc.schema():
            uc.delColumn(olduididx)
    count=0
    allbrains = uc()
    for brain in allbrains:
        #Get a uid for each thingie
        obj = brain.getObject()
        objUID = getattr(obj.aq_base, olduididx, None)        
        if not objUID: continue # not an old style AT
        delattr(obj, olduididx)
        obj._updateCatalog(portal) 
        count+=1
    print >>out, count, "old UID attributes removed."

def migrateSchemas(portal, out):
    at = getToolByName(portal, TOOL_NAME)
    msg = at.manage_updateSchema(update_all=1)    
    print >>out, msg

def migrateMetadata(portal,out):
    print >>out, "Migration of metadata is not implemented."
    
def migrate(self):
    """migrate an AT site"""
    out = StringIO()
    portal = self

    print >>out, "Begin Migration"

    fixArchetypesTool(portal, out)
    migrateSchemas(portal, out)
    migrateMetadata(portal, out)
    migrateUIDs(portal, out)
    migrateReferences(portal,out)
    removeOldUIDs(portal, out)
    print >>out, "Archetypes Migration Successful"
    return out.getvalue()
