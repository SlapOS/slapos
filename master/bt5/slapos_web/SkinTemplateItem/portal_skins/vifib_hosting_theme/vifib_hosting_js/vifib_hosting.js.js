function selectCell(uid,additionnalClass,baseClass,listbox_id){
  
  var checkbox = $("#"+listbox_id+"_cb_"+uid);
  var isChecked = checkbox.is(":checked");
  //Uncheck all
  $("."+listbox_id+"-table :checked").attr("checked", false);
  $("."+listbox_id+"-table ."+baseClass).removeClass(additionnalClass);
 
  if (isChecked == false){
    //check the box which call the function
    var cell = $("#"+listbox_id+"_cell_"+uid);
    cell.addClass(additionnalClass);
    checkbox.attr("checked", true)

  }
  return isChecked == false;

}

function selectSoftwareProduct(uid,additionnalClass,baseClass,listbox_id,product_url,from){
  var isCallingBoxChecked = selectCell(uid,additionnalClass,baseClass,listbox_id);
  if (isCallingBoxChecked == true){
    release_listbox_url = product_url + "/SoftwareProduct_viewAsWeb/release_listbox?came_from=" + from ;
  
    $("#release_listbox_container").load(release_listbox_url);
  }

}

String.prototype.startsWith = function(str)
{return (this.match("^"+str)==str)}

function initCellSelction(additionnalClass,listbox_id)
{
  $("."+listbox_id+"-table :checked").each(function(){
    var id = $(this).attr("id");
    var id_prefix = listbox_id+"_cb_";
    if (id.startsWith(id_prefix))
    {
      uid = id.substring(id_prefix.length,id.length);
      //set the addtional css class
      $("#listbox_cell_"+uid).addClass(additionnalClass);
      
    }
  });
}

function initSoftwareProductList(product_additionnal_class, product_listbox_id){
  
  //Select items
  initCellSelction(product_additionnal_class,product_listbox_id)
  //Show release selection
  $("."+product_additionnal_class+":last").click()
}

function clearField(selector,default_value)
{
  var field = $(selector)
  if (field.val() == default_value){
    field.val('');
  }
}