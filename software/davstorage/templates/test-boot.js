var page = require('webpage').create();
var url = '${:content-url}'

page.open(url,function(status){
  var form = page.evaluate(function(){
    return document.getElementById('login_form');
  });

  if(form === null){
    phantom.exit(1);
  } else {
    phantom.exit();
  }
});
