var page = require('webpage').create();
var url = '${:content-url}'

page.open(url,function(status){
  var text = page.evaluate(function(){
    return document.getElementById('start_button').textContent;
  });

  if(text !== 'Start wizard!'){
    phantom.exit(1);
  } else {
    phantom.exit();
  }
});
