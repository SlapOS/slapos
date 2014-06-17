$(document).ready(function() {
    function doDataUrl (data) {
        var frame_content = document.getElementsByTagName("iframe")[0].contentWindow;
        var b64 = btoa(data);
        dataurl = 'data:text/html;base64,' + b64;
        $("iframe").attr('src', dataurl);
    }
    
    if ( window.self === window.top ) {
        //not in an iframe
        $(".script").click(function(e) {
            e.preventDefault();
            var message = $(this).attr('href');
            var slash_pos = message.search('/');
            //let's differenciate kind of script called
            if ( slash_pos === -1 || slash_pos === 0) {
                url = message;
            }
            else {
                url = '/index.cgi';
            }
           
            $("iframe").attr('src', url + '?script=' + encodeURIComponent(message));
        });
        $(".link").click(function(e) {
            e.preventDefault();
            var url = $(this).attr('href');
            $("iframe").attr('src', url);
        });
    }
    else {
        //in an iframe
        $("body").empty();
    }
});
