$(window).load(function(){
  $(document).ready(function() {
    $("#password_2").keyup(validate);
  });
  function validate() {
    var password1 = $("#password").val();
    var password2 = $("#password_2").val();
      if(password1 == password2) {
          $("#register-button").removeAttr("disabled");
          $("#validate-status").attr("style", "display:none");
      }
      else {
          $("#register-button").attr("disabled", "disabled");
          $("#validate-status").attr("style", "").text("Passwords do not match");
      }   
  }
});