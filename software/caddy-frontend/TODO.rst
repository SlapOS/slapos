Generally things to be done with ``caddy-frontend``:

 * tests: add assertion with results of promises in etc/promise for each partition
 * README: cleanup the documentation, explain various specifics
 * check the whole frontend slave snippet with ``caddy -validate`` during buildout run, and reject if does not pass validation
 * BUG?? check that changing ``apache-certificate`` on master partition results in reloading slave partition
 * (new) ``type:websocket`` slave
 * ``type:eventsource``:

   * **Jérome Perrin**: *For event source, if I understand https://github.com/mholt/caddy/issues/1355 correctly, we could use caddy as a proxy in front of nginx-push-stream . If we have a "central shared" caddy instance, can it handle keeping connections opens for many clients ?*
 * ``check-error-on-caddy-log`` like ``check-error-on-apache-log``

 * move out ``test/utils.py`` and use it from shared python distribution
 * reduce the time of configuration validation (in ``instance-apache-frontend.cfg.in`` sections ``[configtest]``, ``[caddy-configuration]``, ``[nginx-configuration]``), as it is not scalable on frontend with 2000+ slaves (takes few minutes instead of few, < 5, seconds), issue posted `upstream <https://github.com/mholt/caddy/issues/2220>`_
 * drop ``6tunnel`` and use ``bind`` in Caddy configuration, as soon as multiple binds will be possible, tracked in upstream `bind: support multiple values <https://github.com/mholt/caddy/pull/2128>`_ and `ipv6: does not bind on ipv4 and ipv6 for sites that resolve to both <https://github.com/mholt/caddy/issues/864>`_
 * use caddy-frontend in `standalone style playbooks <https://lab.nexedi.com/nexedi/slapos.package/tree/master/playbook/roles/standalone-shared>`_
 * in ``templates/apache-custom-slave-list.cfg.in`` avoid repetetive ``part_list.append`` and use macro like in ERP5 SR (cf `Vincent's comment <https://lab.nexedi.com/nexedi/slapos/merge_requests/373#note_64362>`_)
 * **Jérome Perrin**: consider privacy implications/GDPR compliance of https://caddyserver.com/docs/telemetry and decide if we should leave it enabled.
