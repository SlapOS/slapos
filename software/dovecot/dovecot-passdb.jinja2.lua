function auth_passdb_lookup(req)
  if req.user == "alpha" then
    return dovecot.auth.PASSDB_RESULT_OK, "password=pass"
  end
  return dovecot.auth.PASSDB_RESULT_USER_UNKNOWN, "no such user"
end

function script_init()
  return 0
end

function script_deinit()
end

function auth_userdb_iterate()
  return {"alpha"}
end
