
 * libjpeg62-dev must not be installed before building the SR, or
   Pillow will link against the wrong library version and raise this exception:
        IOError: encoder error -2 when writing image file
        Wrong JPEG library version: library is 62, caller expects 80

 * apt-get install rsync

 * the host needs
    /etc/security/limits.conf
    *                hard    nofile          32768
    *                soft    nofile          32768

 * 'extra' parameters from json or partition configuration can only be strings

 * Required instance parameters:
   (before node software)
   CLOUDOO_URI = http://xxx.xxx.xxx.xxx:8001/
   (before node instance)
   SQLALCHEMY_DATABASE_PASSWORD = .....
   SQLALCHEMY_DATABASE_URI = postgres://user_name:%(password)s@xxx.xxx.xxx.xxx:5432/database_name
   

