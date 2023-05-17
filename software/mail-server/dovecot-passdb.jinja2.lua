function auth_passdb_lookup(req)
  return dovecot.auth.PASSDB_RESULT_OK, string.format("password=%s", req.password)
end

function script_init()
  return 0
end

function script_deinit()
end

function auth_userdb_iterate()
  return {"alpha"}
end
