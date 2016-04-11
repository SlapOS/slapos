"""
WARNING: this script requires proxy manager

This script tries to acquire category values from other objects

base_category_list - list of category values we need to retrieve
object             - object which we want to assign roles to.
"""

result_list = []
user_name = object.Base_getOwnerId()

# XXX Hardcoded role
return {
  'Assignee': [user_name],
}
