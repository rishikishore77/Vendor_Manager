def lookup_name_by_id(collection, id_str, default='N/A'):
    """
    Lookup the 'name' field in a collection by its id string.
    Returns default if not found or id_str is None/empty.
    """
    if not id_str:
        return default
    for item in collection:
        if str(item.get('_id')) == str(id_str):
            return item.get('name') or default
    return default


def lookup_department_by_id(departments, id_str, default='N/A'):
    """
    Lookup a department by ID and return formatted 'name/subdepartment'.
    """
    if not id_str:
        return default
    for dept in departments:
        if str(dept.get('_id')) == str(id_str):
            name = dept.get('name', default)
            subdept = dept.get('subdepartment')
            return f"{name}/{subdept}" if subdept else name
    return default

def find_by_str_id(collection, id_str):
    """
    Generalized lookup: return first object in `collection` whose '_id'
    matches the given `id_str` after converting '_id' to string.
    """
    if not id_str or not collection:
        return None
    for item in collection:
        if str(item.get('_id')) == id_str:
            return item
    return None
