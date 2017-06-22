from Products.ERP5Form.Report import ReportSection
result=[]

result.append(ReportSection(
              path=context.getPhysicalPath(),
              level=3,
              title=context.Base_translateString('Current Computer State'),
              form_id='ComputerModule_viewTicketActivity'))

return result
