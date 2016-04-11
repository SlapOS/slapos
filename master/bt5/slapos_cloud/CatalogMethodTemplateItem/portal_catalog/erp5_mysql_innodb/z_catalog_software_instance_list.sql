DELETE FROM
  software_instance_tree
WHERE
<dtml-in uid>
  uid=<dtml-sqlvar sequence-item type="int"><dtml-if sequence-end><dtml-else> OR </dtml-if>
</dtml-in>
;

<dtml-var "'\0'">

<dtml-let row_list="[]">
  <dtml-in prefix="loop" expr="_.range(_.len(uid))">
    <dtml-if expr="getSpecialiseUid[loop_item]">
      <dtml-call expr="row_list.append([
                uid[loop_item],
                getSpecialiseUid[loop_item]])">
    </dtml-if>
  </dtml-in>

  <dtml-if "row_list">
INSERT INTO
  software_instance_tree
VALUES
    <dtml-in prefix="row" expr="row_list">
(
  <dtml-sqlvar expr="row_item[0]" type="int">,
  <dtml-sqlvar expr="row_item[1]" type="int">
)
<dtml-if sequence-end><dtml-else>,</dtml-if>
    </dtml-in>
  </dtml-if>
</dtml-let>
