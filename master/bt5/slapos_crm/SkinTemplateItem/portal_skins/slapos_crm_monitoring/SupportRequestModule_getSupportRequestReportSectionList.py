from Products.ERP5Form.Report import ReportSection
result=[]


result.append(ReportSection(
              path=context.getPhysicalPath(),
              level=2,
              title=context.Base_translateString('Current State'),
              form_id="SupportRequestModule_viewTicketCurrentStatus"))

result.append(ReportSection(
              path=context.getPhysicalPath(),
              level=2,
              title=context.Base_translateString('Support Request Montly Activity'),
              form_id="SupportRequestModule_viewTicketActivity"))

return result
