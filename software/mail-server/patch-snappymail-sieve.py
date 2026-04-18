import os
import sys

# Ugly but we don't really have a better choice since Snappymail ships minified scripts 
OLD = (
    'case"Forward":u?(t.keep()&&(s.fileinto=1,l.push(a+\'fileinto "INBOX";\')),l.push(a+"redirect "+u+";")):h("redirect");break;'
)

NEW = (
    'case"Forward":u?(t.keep()&&(s.fileinto=1,l.push(a+\'fileinto "INBOX";\')),s.editheader=1,s.variables=1,s.envelope=1,'
    'l.push(a+\'if header :matches "From" "*" {\'),'
    'l.push(a+a+\'set "original_from" "${1}";\'),'
    'l.push(a+"}"),'
    'l.push(a+\'if envelope :matches "to" "*" {\'),'
    'l.push(a+a+\'set "forward_to" "${1}";\'),'
    'l.push(a+"}"),'
    'l.push(a+\'addheader "X-Forwarded-For" "${forward_to}";\'),'
    'l.push(a+\'addheader "X-Forwarded-To" \'+u+";"),'
    'l.push(a+\'if not header :matches "Reply-To" "*" {\'),'
    'l.push(a+a+\'addheader "Reply-To" "${original_from}";\'),'
    'l.push(a+"}"),'
    'l.push(a+\'deleteheader "X-Bogosity";\'),'
    'l.push(a+\'deleteheader "From";\'),'
    'l.push(a+\'addheader "From" "${forward_to}";\'),'
    'l.push(a+"redirect "+u+";")):h("redirect");break;'
)


def main():
    snappymail_dir = sys.argv[1]
    sieve_js = os.path.join(
        snappymail_dir,
        'snappymail', 'v', '2.38.2', 'static', 'js', 'min', 'sieve.min.js',
    )

    with open(sieve_js) as f:
        content = f.read()

    if OLD not in content:
        if NEW in content:
            print("sieve.min.js already patched, skipping")
            return
        raise RuntimeError("Forward case pattern not found in sieve.min.js")

    assert content.count(OLD) == 1, "Pattern found multiple times"

    content = content.replace(OLD, NEW)
    with open(sieve_js, 'w') as f:
        f.write(content)
    print("sieve.min.js patched successfully")


if __name__ == '__main__':
    main()
