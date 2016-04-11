DELETE FROM
  computer_partition
WHERE
<dtml-in uid>
  uid=<dtml-sqlvar sequence-item type="int"><dtml-if sequence-end><dtml-else> OR </dtml-if>
</dtml-in>
;

<dtml-var "'\0'">

<dtml-let row_list="[]">
  <dtml-in prefix="loop" expr="_.range(_.len(uid))">
    <dtml-let free_for_request="ComputerPartition_isFreeForRequest[loop_item]">
    <dtml-let software_type="ComputerPartition_getSoftwareType[loop_item]">
      <dtml-in prefix="url" expr="ComputerPartition_getAvailableSoftwareReleaseUrlStringList[loop_item]" no_push_item>
        <dtml-call expr="row_list.append([
                    uid[loop_item],
                    url_item,
                    free_for_request,
                    software_type])">
      </dtml-in>
    </dtml-let>
    </dtml-let>
  </dtml-in>

  <dtml-if "row_list">
INSERT INTO
  computer_partition
VALUES
    <dtml-in prefix="row" expr="row_list">
(
  <dtml-sqlvar expr="row_item[0]" type="int">,
  <dtml-sqlvar expr="row_item[1]" type="string">,
  <dtml-sqlvar expr="row_item[2]" type="int">,
  <dtml-sqlvar expr="row_item[3]" type="string">
)
<dtml-if sequence-end><dtml-else>,</dtml-if>
    </dtml-in>
  </dtml-if>
</dtml-let>
