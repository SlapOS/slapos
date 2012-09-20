import hashlib
def getSha512Hexdiest(s):
  return hashlib.sha512(s).hexdigest()
