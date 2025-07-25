
-- md5sum
local function band(a, b)
    local result = 0
    local bitval = 1
    while a > 0 and b > 0 do
        if a % 2 == 1 and b % 2 == 1 then
            result = result + bitval
        end
        bitval = bitval * 2
        a = math.floor(a / 2)
        b = math.floor(b / 2)
    end
    return result
end

local function bor(a, b)
    local result = 0
    local bitval = 1
    while a > 0 or b > 0 do
        if (a % 2 == 1) or (b % 2 == 1) then
            result = result + bitval
        end
        bitval = bitval * 2
        a = math.floor(a / 2)
        b = math.floor(b / 2)
    end
    return result
end

local function bxor(a, b)
    local result = 0
    local bitval = 1
    while a > 0 or b > 0 do
        if (a % 2) ~= (b % 2) then
            result = result + bitval
        end
        bitval = bitval * 2
        a = math.floor(a / 2)
        b = math.floor(b / 2)
    end
    return result
end

local function bnot(a)
    return bxor(a, 0xFFFFFFFF)
end

local function lshift(a, disp)
    return (a * (2 ^ disp)) % (2 ^ 32)
end

local function rshift(a, disp)
    return math.floor(a / (2 ^ disp))
end

local function md5_transform(a, b, c, d, x, s, ac)
    local function f(x, y, z) return bor(band(x, y), band(bnot(x), z)) end
    local function g(x, y, z) return bor(band(x, z), band(y, bnot(z))) end
    local function h(x, y, z) return bxor(x, bxor(y, z)) end
    local function i(x, y, z) return bxor(y, bor(x, bnot(z))) end
    
    local function rotleft(value, amount)
        local lbits = lshift(value, amount)
        local rbits = rshift(value, (32 - amount))
        return bor(lbits, rbits)
    end
    
    local function ff(a, b, c, d, x, s, ac)
        a = band(a + f(b, c, d) + x + ac, 0xFFFFFFFF)
        return band(rotleft(a, s) + b, 0xFFFFFFFF)
    end
    
    local function gg(a, b, c, d, x, s, ac)
        a = band(a + g(b, c, d) + x + ac, 0xFFFFFFFF)
        return band(rotleft(a, s) + b, 0xFFFFFFFF)
    end
    
    local function hh(a, b, c, d, x, s, ac)
        a = band(a + h(b, c, d) + x + ac, 0xFFFFFFFF)
        return band(rotleft(a, s) + b, 0xFFFFFFFF)
    end
    
    local function ii(a, b, c, d, x, s, ac)
        a = band(a + i(b, c, d) + x + ac, 0xFFFFFFFF)
        return band(rotleft(a, s) + b, 0xFFFFFFFF)
    end
    
    return ff, gg, hh, ii
end

local function md5(input)
    local h = {0x67452301, 0xEFCDAB89, 0x98BADCFE, 0x10325476}
    
    local msg = input
    local msg_len = #msg
    local bit_len = msg_len * 8
    
    msg = msg .. string.char(0x80)
    
    local padding_len = 56 - ((msg_len + 1) % 64)
    if padding_len < 0 then padding_len = padding_len + 64 end
    msg = msg .. string.rep(string.char(0), padding_len)
    
    local low = bit_len % (2^32)
    local high = math.floor(bit_len / (2^32))
    msg = msg .. string.char(
        low % 256, math.floor(low / 256) % 256,
        math.floor(low / 65536) % 256, math.floor(low / 16777216) % 256,
        high % 256, math.floor(high / 256) % 256,
        math.floor(high / 65536) % 256, math.floor(high / 16777216) % 256
    )
    
    for chunk_start = 1, #msg, 64 do
        local chunk = msg:sub(chunk_start, chunk_start + 63)
        local w = {}
        
        for i = 0, 15 do
            local j = i * 4 + 1
            local b1, b2, b3, b4 = chunk:byte(j, j + 3)
            w[i] = b1 + b2 * 256 + b3 * 65536 + b4 * 16777216
        end
        
        local a, b, c, d = h[1], h[2], h[3], h[4]
        
        local ff, gg, hh, ii = md5_transform()
        
        a = ff(a, b, c, d, w[0], 7, 0xD76AA478)   d = ff(d, a, b, c, w[1], 12, 0xE8C7B756)
        c = ff(c, d, a, b, w[2], 17, 0x242070DB)  b = ff(b, c, d, a, w[3], 22, 0xC1BDCEEE)
        a = ff(a, b, c, d, w[4], 7, 0xF57C0FAF)   d = ff(d, a, b, c, w[5], 12, 0x4787C62A)
        c = ff(c, d, a, b, w[6], 17, 0xA8304613)  b = ff(b, c, d, a, w[7], 22, 0xFD469501)
        a = ff(a, b, c, d, w[8], 7, 0x698098D8)   d = ff(d, a, b, c, w[9], 12, 0x8B44F7AF)
        c = ff(c, d, a, b, w[10], 17, 0xFFFF5BB1) b = ff(b, c, d, a, w[11], 22, 0x895CD7BE)
        a = ff(a, b, c, d, w[12], 7, 0x6B901122)  d = ff(d, a, b, c, w[13], 12, 0xFD987193)
        c = ff(c, d, a, b, w[14], 17, 0xA679438E) b = ff(b, c, d, a, w[15], 22, 0x49B40821)
        
        a = gg(a, b, c, d, w[1], 5, 0xF61E2562)   d = gg(d, a, b, c, w[6], 9, 0xC040B340)
        c = gg(c, d, a, b, w[11], 14, 0x265E5A51) b = gg(b, c, d, a, w[0], 20, 0xE9B6C7AA)
        a = gg(a, b, c, d, w[5], 5, 0xD62F105D)   d = gg(d, a, b, c, w[10], 9, 0x02441453)
        c = gg(c, d, a, b, w[15], 14, 0xD8A1E681) b = gg(b, c, d, a, w[4], 20, 0xE7D3FBC8)
        a = gg(a, b, c, d, w[9], 5, 0x21E1CDE6)   d = gg(d, a, b, c, w[14], 9, 0xC33707D6)
        c = gg(c, d, a, b, w[3], 14, 0xF4D50D87)  b = gg(b, c, d, a, w[8], 20, 0x455A14ED)
        a = gg(a, b, c, d, w[13], 5, 0xA9E3E905)  d = gg(d, a, b, c, w[2], 9, 0xFCEFA3F8)
        c = gg(c, d, a, b, w[7], 14, 0x676F02D9)  b = gg(b, c, d, a, w[12], 20, 0x8D2A4C8A)
        
        a = hh(a, b, c, d, w[5], 4, 0xFFFA3942)   d = hh(d, a, b, c, w[8], 11, 0x8771F681)
        c = hh(c, d, a, b, w[11], 16, 0x6D9D6122) b = hh(b, c, d, a, w[14], 23, 0xFDE5380C)
        a = hh(a, b, c, d, w[1], 4, 0xA4BEEA44)   d = hh(d, a, b, c, w[4], 11, 0x4BDECFA9)
        c = hh(c, d, a, b, w[7], 16, 0xF6BB4B60)  b = hh(b, c, d, a, w[10], 23, 0xBEBFBC70)
        a = hh(a, b, c, d, w[13], 4, 0x289B7EC6)  d = hh(d, a, b, c, w[0], 11, 0xEAA127FA)
        c = hh(c, d, a, b, w[3], 16, 0xD4EF3085)  b = hh(b, c, d, a, w[6], 23, 0x04881D05)
        a = hh(a, b, c, d, w[9], 4, 0xD9D4D039)   d = hh(d, a, b, c, w[12], 11, 0xE6DB99E5)
        c = hh(c, d, a, b, w[15], 16, 0x1FA27CF8) b = hh(b, c, d, a, w[2], 23, 0xC4AC5665)
        
        a = ii(a, b, c, d, w[0], 6, 0xF4292244)   d = ii(d, a, b, c, w[7], 10, 0x432AFF97)
        c = ii(c, d, a, b, w[14], 15, 0xAB9423A7) b = ii(b, c, d, a, w[5], 21, 0xFC93A039)
        a = ii(a, b, c, d, w[12], 6, 0x655B59C3)  d = ii(d, a, b, c, w[3], 10, 0x8F0CCC92)
        c = ii(c, d, a, b, w[10], 15, 0xFFEFF47D) b = ii(b, c, d, a, w[1], 21, 0x85845DD1)
        a = ii(a, b, c, d, w[8], 6, 0x6FA87E4F)   d = ii(d, a, b, c, w[15], 10, 0xFE2CE6E0)
        c = ii(c, d, a, b, w[6], 15, 0xA3014314)  b = ii(b, c, d, a, w[13], 21, 0x4E0811A1)
        a = ii(a, b, c, d, w[4], 6, 0xF7537E82)   d = ii(d, a, b, c, w[11], 10, 0xBD3AF235)
        c = ii(c, d, a, b, w[2], 15, 0x2AD7D2BB)  b = ii(b, c, d, a, w[9], 21, 0xEB86D391)
        
        h[1] = band(h[1] + a, 0xFFFFFFFF)
        h[2] = band(h[2] + b, 0xFFFFFFFF)
        h[3] = band(h[3] + c, 0xFFFFFFFF)
        h[4] = band(h[4] + d, 0xFFFFFFFF)
    end
    
    local function to_hex(n)
        return string.format("%02x%02x%02x%02x",
            n % 256, math.floor(n / 256) % 256,
            math.floor(n / 65536) % 256, math.floor(n / 16777216) % 256)
    end
    
    local full_hash = to_hex(h[1]) .. to_hex(h[2]) .. to_hex(h[3]) .. to_hex(h[4])
    return "0x" .. string.upper(string.sub(full_hash, -16))
end

local QueryDigestFingerprint = {}
QueryDigestFingerprint.__index = QueryDigestFingerprint

function QueryDigestFingerprint:new()
    local obj = {}
    setmetatable(obj, QueryDigestFingerprint)
    return obj
end

local function trim(str)
    return str:match("^%s*(.-)%s*$")
end

-- port of pt-query-digest's fingerprint algorithm, from version 3.0.3
-- pt-query-digest is copyright 2008-2017 Percona LLC and/or its affiliates.
function QueryDigestFingerprint:fingerprint(query)
    if query:match("^SELECT /%*!40001 SQL_NO_CACHE %*/ %* FROM `") then
        return "mysqldump"
    end
    
    if query:match("/%*%w+%.%w+:[0-9]/[0-9]%*/") then
        return "percona-toolkit"
    end
    
    if query:match("^%s*administrator command: ") then
        return query
    end
    
    local call_match = query:match("^%s*(call%s+%S+)%(")
    if call_match then
        return call_match:lower()
    end
    
    local insert_beginning = query:match("^((?:INSERT|REPLACE)(?: IGNORE)?%s+INTO.+?VALUES%s*%(.-%))%s*,%s*%(")
    if insert_beginning then
        query = insert_beginning
    end
    
    query = query:gsub("/%*.-%*/", "")
    query = query:gsub("%-%-[^\r\n]*", "")
    query = query:gsub("#[^\r\n]*", "")
    
    local use_result = query:gsub("^%s*use%s+%S+%s*$", "use ?")
    if use_result ~= query then
        return use_result
    end
    query = use_result
    
    query = query:gsub("\\[\"']", "")
    
    query = query:gsub('".-"', "?")
    query = query:gsub("'.-'", "?")
    
    query = query:gsub("%f[%w]false%f[%W]", "?")
    query = query:gsub("%f[%w]true%f[%W]", "?")
    
    query = query:gsub("[0-9+%-][0-9a-f.xb+%-]*", "?")
    
    query = query:gsub("[xb.+%-]%?", "?")
    
    query = trim(query)
    
    query = query:gsub("%s+", " ")
    
    query = query:lower()
    
    query = query:gsub("%f[%w]null%f[%W]", "?")
    
    query = query:gsub("(%f[%w](?:in|values?)%f[%W])(?:%s*,%s*%(%s*%?%s*,%s*%s*%))+", "%1(?+)")
    
    query = query:gsub("(%f[%w]select%s.-)(%s+union(?:%s+all)?)%s+%1", "%1 /*repeat%2*/")
    
    query = query:gsub("%f[%w]limit%s+%?(?:,%s*%?|%s+offset%s+%?)%f[%W]", "limit ?")
    
    if query:match("%f[%w]order%s+by%f[%W]") then
        query = query:gsub("(%S+)%s+asc%f[%W]", "%1")
    end
    
    return query
end

function QueryDigestFingerprint:fingerprint_md5(query)
    local fingerprint = self:fingerprint(query)
    return md5(fingerprint)
end

qdf = QueryDigestFingerprint:new()

function query_fingerprint_filter(tag, timestamp, record)
    record.field_query_fingerprint = qdf:fingerprint_md5(record.intermediate_query)
    return 1, timestamp, record
end
