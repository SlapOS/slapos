var page = require('webpage').create();
var url = '${:content-url}';

page.open(url, function(status){
  page.evaluate(function(){
    function eventFire(el, etype){
      if (el.fireEvent) {
        (el.fireEvent('on' + etype));
      } else {
        var evObj = document.createEvent('Events');
        evObj.initEvent(etype, true, false);
        el.dispatchEvent(evObj);
      }
    }

    eventFire(document.getElementById('start_button'),'click');

    document.getElementsByName('ADMIN_USER_LOGIN')[0].setValue('${:user}');
    document.getElementsByName('ADMIN_USER_NAME')[0].setValue('${:user}');
    document.getElementsByName('ADMIN_USER_PASS')[0].setValue('${:password}');
    document.getElementsByName('ADMIN_USER_PASS2')[0].setValue('${:password}');
    document.getElementsByName('STORAGE_TYPE')[0].setValue('${:storage-type}');
    var button = document.getElementById('save_button')
    button.removeClassName('disabled');
    
    eventFire(button,'click');
    
  });
  phantom.exit();
});
