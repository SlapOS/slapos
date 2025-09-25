import secrets
import string
import dns.resolver
import datetime
import logging

# --- CONFIGURATION ---
TOKEN_LENGTH = 32  # Strong, random tokens
TOKEN_TTL = 3600   # Token expires in seconds (1 hour)

# Initialize logging
logging.basicConfig(
    format="%(asctime)s %(levelname)s: %(message)s",
    level=logging.INFO
)

class Recipe(object):
  def __init__(self, *args, **kwargs):
    pass

  def install(self):
    return []

  def update(self):
    return self.install()



# --- TOKEN MANAGEMENT ---
class DomainVerificationManager:
    def __init__(self):
        self._tokens = {}  # {domain: (token, expiry)}

    def generate_token(self, domain):
        # Use a cryptographically strong random token
        token = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(TOKEN_LENGTH))
        expiry = datetime.datetime.utcnow() + datetime.timedelta(seconds=TOKEN_TTL)
        self._tokens[domain] = (token, expiry)
        logging.info(f"Generated verification token for {domain}, expires at {expiry}.")
        return token

    def is_token_valid(self, domain):
        entry = self._tokens.get(domain)
        if not entry:
            return False, "No token issued."
        token, expiry = entry
        if datetime.datetime.utcnow() > expiry:
            del self._tokens[domain]
            return False, "Token expired."
        return True, token

# --- DNS LOOKUP LOGIC ---
def verify_domain(domain, expected_token, dnssec_required=False):
    try:
        answers = dns.resolver.resolve(domain, 'TXT', lifetime=10)
        for rdata in answers:
            texts = [txt.decode() if hasattr(txt, 'decode') else txt for txt in rdata.strings]
            if expected_token in texts:
                logging.info(f"[{domain}] Verification token found in DNS TXT record.")
                # (Optional) Add further DNSSEC validation here with 'dns.resolver.Resolver' config.
                return True
        logging.warning(f"[{domain}] Verification token not found in DNS TXT records.")
        return False
    except Exception as e:
        logging.error(f"[{domain}] DNS query failed: {e}")
        return False

# --- USAGE EXAMPLE ---
if __name__ == "__main__":
    domain = "example.com"
    dv = DomainVerificationManager()
    token = dv.generate_token(domain)
    print(f"Add this DNS TXT record to {domain}:")
    print(f"_verify.{domain} IN TXT \"{token}\"")

    # Wait for DNS propagation before running the check!
    input("Press Enter when DNS TXT record has propagated...")

    valid, token_or_reason = dv.is_token_valid(domain)
    if valid:
        verified = verify_domain(f"_verify.{domain}", token_or_reason)
        print("Domain verified!" if verified else "Verification failed.")
    else:
        print("Token invalid:", token_or_reason)