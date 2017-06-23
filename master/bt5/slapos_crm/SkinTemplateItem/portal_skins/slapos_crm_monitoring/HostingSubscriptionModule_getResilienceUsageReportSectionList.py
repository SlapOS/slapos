from Products.ERP5Form.Report import ReportSection
result=[]

result.append(ReportSection(
              path=context.getPhysicalPath(),
              level=4,
              title=context.Base_translateString('Resilience Status per User'),
              form_id='HostingSubscriptionModule_viewResilienceUsage'))

return result
