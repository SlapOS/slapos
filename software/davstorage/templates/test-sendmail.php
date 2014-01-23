#!${:php-location}
<?php

require_once("${:htdocs-location}/plugins/mailer.phpmailer-lite/lib/class.phpmailer-lite.php");

$mailer = new PHPMailerLite(true);
$mailer->SetFrom('test@couscous.com');
$mailer->AddAddress('couscous@test.com');
$mailer->Subject = 'test';
$mailer->Body = 'test';

$mailer->Send();
?>