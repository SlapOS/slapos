from Products.ERP5Form.Report import ReportSection
result=[]
result.append(ReportSection(
              path=context.getPhysicalPath(),
              title=context.Base_translateString('Resource Consumption'),
              form_id='WebSection_viewConsuptionReportList'))

return result
