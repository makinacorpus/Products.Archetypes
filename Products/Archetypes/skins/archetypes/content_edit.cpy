## Script (Python) "content_edit"
##title=Edit content
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind state=state
##bind subpath=traverse_subpath
##parameters=id=''
##
REQUEST = context.REQUEST

try:
    new_context = context.portal_factory.doCreate(context, id)
except AttributeError:
    # Fallback for AT + plain CMF where we don't have a portal_factory
    new_context = context
new_context.processForm()

portal_status_message = context.translate(
    msgid='message_content_changes_saved',
    domain='archetypes',
    default='Content changes saved.')

portal_status_message = REQUEST.get('portal_status_message', portal_status_message)

# handle navigation for multi-page edit forms
next = not REQUEST.get('form_next', None) is None
previous = not REQUEST.get('form_previous', None) is None
fieldset = REQUEST.get('fieldset', None)
schemata = new_context.Schemata()

if next or previous:
    s_names = [s for s in schemata.keys() if s != 'metadata']

    if previous:
        s_names.reverse()

    next_schemata = None
    try:
        index = s_names.index(fieldset)
    except ValueError:
        raise 'Non-existing fieldset: %s' % fieldset
    else:
        index += 1
        if index < len(s_names):
            next_schemata = s_names[index]
            return state.set(status='next_schemata',
                             context=new_context,
                             fieldset=next_schemata,
                             portal_status_message=portal_status_message)

    if next_schemata != None:
        return state.set(status='next_schemata', \
                 context=new_context, \
                 fieldset=next_schemata, \
                 portal_status_message=portal_status_message)
    else:
        raise 'Unable to find next field set after %s' % fieldset

env = state.kwargs
reference_source_url = env.get('reference_source_url')
if reference_source_url is not None:
    reference_source_url = env['reference_source_url'].pop()
    reference_source_field = env['reference_source_field'].pop()
    reference_source_fieldset = env['reference_source_fieldset'].pop()
    portal = context.portal_url.getPortalObject()
    reference_obj = portal.restrictedTraverse(reference_source_url)
    portal_status_message = context.translate(
        msgid='message_reference_added',
        domain='archetypes',
        default='Reference Added.')

    # update session saved data
    SESSION = context.REQUEST.SESSION
    saved_dic = SESSION.get(reference_obj.getId(), None)
    if saved_dic:
        saved_value = saved_dic.get(reference_source_field, None)
        if same_type(saved_value, []):
            # reference_source_field is a multiValued field, right!?
            saved_value.append(new_context.UID())
        else:
            saved_value = new_context.UID()
        saved_dic[reference_source_field] = saved_value
        SESSION.set(reference_obj.getId(), saved_dic)
    
    kwargs = {
        'status':'success_add_reference',
        'context':reference_obj,
        'portal_status_message':portal_status_message,
        'fieldset':reference_source_fieldset,
        'field':reference_source_field,
        #reference_source_field:new_context.UID(),
        }
    return state.set(**kwargs)

if state.errors:
    errors = state.errors
    s_items = [(s, schemata[s].keys()) for s in schemata.keys()]
    fields = []
    for s, f_names in s_items:
        for f_name in f_names:
            fields.append((s, f_name))
    for s_name, f_name in fields:
        if errors.has_key(f_name):
            REQUEST.set('fieldset', s_name)
            return state.set(
                status='failure',
                context=new_context,
                portal_status_message=portal_status_message)

return state.set(status='success',
                 context=new_context,
                 portal_status_message=portal_status_message)