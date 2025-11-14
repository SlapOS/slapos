# mail-server

- Local IMAP / SMTP mail server using Dovecot and Postfix
- Runs on port 10143 and 10025. This will be configurable at a later point
- Designed to be deployed on 4G / 5G base stations such as ORS

This SR can be used along with the `mail-server-relay` SR to connect to an 
external mail delivery service, or to perform load balancing on the sending
and receiving of e-mails.