# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2010 Nexedi SA and Contributors. All Rights Reserved.
#          Nicolas Delaby <nicolas@nexedi.com>
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly advised to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################
import unittest
from VifibMixin import testVifibMixin
from Products.ERP5Type.tests.backportUnittest import expectedFailure

class TestVifibXHTML(testVifibMixin):
  run_all_test = 1

  def getTitle(self):
    return "Vifib XHTML"

  def changeSkin(self, skin_name):
    """
      Change current Skin
    """
    request = self.app.REQUEST
    self.getPortal().portal_skins.changeSkin(skin_name)
    request.set('portal_skin', skin_name)

  def test_deadProxyFields(self):
    # check that all proxy fields defined in business templates have a valid
    # target
    skins_tool = self.portal.portal_skins
    error_list = []

    for skin_name, skin_folder_string in skins_tool.getSkinPaths():
      skin_folder_id_list = skin_folder_string.split(',')
      self.changeSkin(skin_name)

      for skin_folder_id in skin_folder_id_list:
        for field_path, field in skins_tool[skin_folder_id].ZopeFind(
                  skins_tool[skin_folder_id], 
                  obj_metatypes=['ProxyField'], search_sub=1):
          template_field = field.getTemplateField(cache=False)
          if template_field is None:
            # Base_viewRelatedObjectList (used for proxy listbox ids on
            # relation fields) is an exception, the proxy field has no target
            # by default.
            if field_path != 'Base_viewRelatedObjectList/listbox':
              error_list.append((skin_name, field_path, field.get_value('form_id'),
                                 field.get_value('field_id')))

    if error_list:
      message = '\nDead proxy field list\n'
      for error in error_list:
        message += '\t%s\n' % str(error)
      self.fail(message)
    
  def test_emptySelectionNameInListbox(self):
    # check all empty selection name in listboxes
    skins_tool = self.portal.portal_skins
    error_list = []
    for form_path, form in skins_tool.ZopeFind(
              skins_tool, obj_metatypes=['ERP5 Form'], search_sub=1):
      try:
       fields = form.get_fields()
      except AttributeError, e:
        print "%s is broken: %s" % (form_path, e)
      for field in fields:
        if field.meta_type =='ListBox':
          selection_name = field.get_value("selection_name")
          if selection_name in ("",None):
            error_list.append(form_path)
    self.assertEquals(error_list, [])

  def test_callableListMethodInListbox(self):
    # check all list_method in listboxes
    skins_tool = self.portal.portal_skins
    error_list = []
    for form_path, form in skins_tool.ZopeFind(
              skins_tool, obj_metatypes=['ERP5 Form'], search_sub=1):
      try:
       fields = form.get_fields()
      except AttributeError, e:
        print "%s is broken: %s" % (form_path, e)
      for field in fields:
        if field.meta_type == 'ListBox':
          list_method = field.get_value("list_method")
          if list_method:
            if isinstance(list_method, str):
              method = getattr(self.portal, list_method)
            else:
              method = list_method
            if not callable(method):
              error_list.append(form_path)
    self.assertEquals(error_list, [])

  @expectedFailure
  def test_configurationOfFieldLibrary(self):
    self.login()
    error_list = []
    for business_template in self.portal.portal_templates.searchFolder(
          title='vifib_%'):
      # XXX Impossible to filter by installation state, as it is not catalogued
      business_template = business_template.getObject()
      for modifiable_field in business_template.BusinessTemplate_getModifiableFieldList():
        # Do not consider 'Check delegated values' as an error
        if modifiable_field.choice_item_list[0][1] != \
                                              "0_check_delegated_value":
          error_list.append((business_template.getTitle(),
            modifiable_field.object_id,
            modifiable_field.choice_item_list[0][0]))
    if error_list:
      message = '%s fields to modify' % len(error_list)
      message += '\n\t' + '\n\t'.join(bt_title + ':' + fieldname + ": " + \
          message for bt_title, fieldname, message in error_list)
      self.fail(message)

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibXHTML))
  return suite
