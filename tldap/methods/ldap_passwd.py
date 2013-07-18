"""
ldaputil.passwd - client-side password setting
(c) by Michael Stroeder <michael@stroeder.com>

This module is distributed under the terms of the
GPL (GNU GENERAL PUBLIC LICENSE) Version 2
(see http://www.gnu.org/copyleft/gpl.html)

Python compability note:
This module only works with Python 1.6+ since all string parameters
are assumed to be Unicode objects and string methods are used instead
string module.
"""

__version__ = '0.1.0'

import random
import ldap
try:
    # Recent versions of Python have hashlib
    from hashlib import md5
    from hashlib import sha1 as sha
except ImportError:
    # Backwards compatability with older Python
    from md5 import md5
    from sha import sha
import string


# Alphabet for encrypted passwords (see module crypt)
CRYPT_ALPHABET = './0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'

# Try to determine the hash types available on the current system by
# checking all required modules are in place.
# After all AVAIL_USERPASSWORD_SCHEMES is a list of tuples containing
# [(hash-id,(hash-description)].
AVAIL_USERPASSWORD_SCHEMES = {
    'sha': 'userPassword SHA-1',
    'ssha': 'userPassword salted SHA-1',
    'md5': 'userPassword MD5',
    'smd5': 'userPassword salted MD5',
    'crypt': 'userPassword Unix crypt',
    'md5-crypt': 'userPassword MD5 crypt',
    '': 'userPassword plain text',
}

AVAIL_AUTHPASSWORD_SCHEMES = {
    'sha1': 'authPassword SHA-1',
    'md5': 'authPassword MD5',
}

_UnicodeType = type(u'')


def _remove_dict_items(l, rl):
    """
    Not for public use:
    Remove a list item ignoring ValueError: list.remove(x): x not in list
    """
    for i in rl:
        try:
            del l[i]
        except KeyError:
            pass

try:
    import base64
except ImportError:
    _remove_dict_items(AVAIL_USERPASSWORD_SCHEMES, ['md5', 'smd5', 'sha', 'ssha'])
    _remove_dict_items(AVAIL_AUTHPASSWORD_SCHEMES, ['md5', 'sha1'])
else:
    try:
        # random is needed for salted hashs
        import random
    except ImportError:
        _remove_dict_items(AVAIL_USERPASSWORD_SCHEMES, ['crypt', 'smd5', 'ssha'])
        _remove_dict_items(AVAIL_AUTHPASSWORD_SCHEMES, ['md5', 'sha1'])
    else:
        random.seed()
    try:
        import hashlib
    except ImportError:
        try:
            from sha import sha
        except ImportError:
            _remove_dict_items(AVAIL_USERPASSWORD_SCHEMES, ['sha', 'ssha'])
            _remove_dict_items(AVAIL_AUTHPASSWORD_SCHEMES, ['sha1'])
    try:
        import hashlib
    except ImportError:
        try:
            from md5 import md5
        except ImportError:
            _remove_dict_items(AVAIL_USERPASSWORD_SCHEMES, ['md5', 'smd5'])
            _remove_dict_items(AVAIL_AUTHPASSWORD_SCHEMES, ['md5'])
    try:
        import crypt
    except ImportError:
        _remove_dict_items(AVAIL_USERPASSWORD_SCHEMES, ['crypt'])


def _salt(saltLen=2, saltAlphabet=None):
    """
    Create a random salt.

    saltLen
            Requested length of salt string.
    saltAlphabet
            If non-zero string it is assumed to contain all valid chars
            for the salt. If zero-length or None the salt returned is an
            arbitrary octet string.
    """
    salt = []
    if saltAlphabet:
        saltAlphabetBounce = len(saltAlphabet)-1
        for i in range(saltLen):
            salt.append(saltAlphabet[random.randrange(0, saltAlphabetBounce)])
    else:
        for i in range(saltLen):
            salt.append(chr(random.randrange(0, 255)))
    return ''.join(salt)


class Password:
    """
    Base class for plain-text LDAP passwords.
    """

    def __init__(self, l, dn=None, charset='utf-8'):
        """
        l
                LDAPObject instance to operate with. The application
                is responsible to bind with appropriate bind DN before(!)
                creating the Password instance.
        dn
                string object with DN of entry
        charset
                Character set for encoding passwords. Note that this might
                differ from the character set used for the normal directory strings.
        """
        self._l = l
        self._dn = dn
        self._multiple = 0
        self._charset = charset
        if not dn is None:
            result = self._l.search_s(
                self._dn, ldap.SCOPE_BASE, '(objectClass=*)', [self.passwordAttributeType]
            )
            if result:
                entry_data = result[0][1]
                self._passwordAttributeValue = entry_data.get(
                    self.passwordAttributeType, entry_data.get(self.passwordAttributeType.lower(), [])
                )
            else:
                self._passwordAttributeValue = []
        else:
            self._passwordAttributeValue = []

    def _compareSinglePassword(self, testPassword, singlePasswordValue):
        """
        Compare testPassword with encoded password in singlePasswordValue.

        testPassword
                Plain text password for testing
        singlePasswordValue
                password to verify against
        """
        return testPassword == singlePasswordValue

    def comparePassword(self, testPassword):
        """
        Return 1 if testPassword is in self._passwordAttributeValue
        """
        if type(testPassword) == _UnicodeType:
            testPassword = testPassword.encode(self._charset)
        for p in self._passwordAttributeValue:
            if self._compareSinglePassword(testPassword, p):
                return 1
        return 0

    def _delOldPassword(self, oldPassword):
        """
        Return list with all occurences of oldPassword being removed.
        """
        return [
            p
            for p in self._passwordAttributeValue
            if not self._compareSinglePassword(oldPassword, p.strip())
        ]

    def encodePassword(self, plainPassword, scheme=None):
        """
        encode plainPassword into plain text password
        """
        if type(plainPassword) == _UnicodeType:
            plainPassword = plainPassword.encode(self._charset)
        return plainPassword

    def changePassword(self, oldPassword=None, newPassword=None, scheme=None):
        """
        oldPassword
            Old password associated with entry.
            If a Unicode object is supplied it will be encoded with
            self._charset.
        newPassword        
            New password for entry.
            If a Unicode object is supplied it will be encoded with
            charset before being transferred to the directory.
        scheme
                Hashing scheme to be used for encoding password.
                Default is plain text.
        charset
                This character set is used to encode passwords
                in case oldPassword and/or newPassword are Unicode objects.
        """
        if not oldPassword is None and type(oldPassword) == _UnicodeType:
            oldPassword = oldPassword.encode(charset)
        if self._multiple and not oldPassword is None:
            newPasswordValueList = self._delOldPassword(oldPassword)
        else:
            newPasswordValueList = []
        newPasswordValue = self.encodePassword(newPassword, scheme)
        newPasswordValueList.append(newPasswordValue)
        self._storePassword(oldPassword, newPasswordValueList)
        # In case a new password was auto-generated the application
        # has to know it => return it as result
        return newPassword

    def _storePassword(self, oldPassword, newPasswordValueList):
        """Replace the password value completely"""

        self._l.modify_s(
            self._dn,
            [
                (ldap.MOD_REPLACE, self.passwordAttributeType, newPasswordValueList)
            ]
        )


class UserPassword(Password):
    """
    Class for LDAP password changing in userPassword attribute

    RFC 2307:
        http://www.ietf.org/rfc/rfc2307.txt
    OpenLDAP FAQ:
        http://www.openldap.org/faq/data/cache/419.html
    Netscape Developer Docs:
        http://developer.netscape.com/docs/technote/ldap/pass_sha.html
    """
    passwordAttributeType='userPassword'
    _hash_bytelen = {'md5':16, 'sha':20}

    def __init__(self, l=None, dn=None, charset='utf-8', multiple=0):
        """
        Like CharsetPassword.__init__() with one additional parameter:
        multiple
                Allow multi-valued password attribute.
                Default is single-valued (flag is 0).
        """
        self._multiple = multiple
        Password.__init__(self, l, dn, charset)

    def _hashPassword(self, password, scheme, salt=None):
        """
        Return hashed password (including salt).
        """
        scheme = scheme.lower()
        if not scheme in AVAIL_USERPASSWORD_SCHEMES.keys():
            raise ValueError, 'Hashing scheme %s not supported for class %s.' % (
                scheme, self.__class__.__name__
            )
            raise ValueError, 'Hashing scheme %s not supported.' % (scheme)
        if salt is None:
            if scheme=='crypt':
                salt = _salt(saltLen=2, saltAlphabet=CRYPT_ALPHABET)
            elif scheme in ['smd5', 'ssha']:
                salt = _salt(saltLen=4, saltAlphabet=None)
            else:
                salt = ''
        if scheme=='crypt':
            return crypt.crypt(password, salt)
        elif scheme in ['md5', 'smd5']:
            return base64.encodestring(md5(password+salt).digest()+salt).strip()
        elif scheme in ['sha', 'ssha']:
            return base64.encodestring(sha(password+salt).digest()+salt).strip()
        else:
            return password

    def _compareSinglePassword(self, testPassword, singlePasswordValue, charset='utf-8'):
        """
        Compare testPassword with encoded password in singlePasswordValue.

        testPassword
                Plain text password for testing. If Unicode object
                it is encoded using charset.
        singlePasswordValue
                {scheme} encrypted password
        """
        singlePasswordValue = singlePasswordValue.strip()
        try:
            scheme, encoded_p = singlePasswordValue[singlePasswordValue.find('{')+1:].split('}', 1)
        except ValueError:
            scheme, encoded_p = '', singlePasswordValue
        scheme = scheme.lower()
        if scheme in ['md5', 'sha', 'smd5', 'ssha']:
            hashed_p = base64.decodestring(encoded_p)
            if scheme in ['smd5', 'ssha']:
                pos = self._hash_bytelen[scheme[1:]]
                cmp_password, salt = hashed_p[:pos], hashed_p[pos:]
            else:
                cmp_password, salt = hashed_p, ''
        hashed_password = self._hashPassword(testPassword, scheme, salt)
        return hashed_password == encoded_p

    def encodePassword(self, plainPassword, scheme):
        """
        encode plainPassword according to RFC2307 password attribute syntax
        """
        plainPassword = Password.encodePassword(self, plainPassword)
        if scheme:
            # Brutal Hack
            if scheme == 'md5-crypt':
                return '{crypt}%s' % md5crypt(plainPassword)

            return ('{%s}%s' % (
                scheme.upper(),
                self._hashPassword(plainPassword, scheme)
            )).encode('ascii')
        else:
            return plainPassword


# Based on FreeBSD src/lib/libcrypt/crypt.c 1.2
# http://www.freebsd.org/cgi/cvsweb.cgi/~checkout~/src/lib/libcrypt/crypt.c?rev=1.2&content-type=text/plain

# Original license:
# * "THE BEER-WARE LICENSE" (Revision 42):
# * <phk@login.dknet.dk> wrote this file.    As long as you retain this notice you
# * can do whatever you want with this stuff. If we meet some day, and you think
# * this stuff is worth it, you can buy me a beer in return.     Poul-Henning Kamp

# This port adds no further stipulations.    I forfeit any copyright interest.
def md5crypt(password, salt=None, magic='$1$'):

    if salt is None:
        salt = _salt(saltLen=8, saltAlphabet=string.letters + string.digits)
        # /* The password first, since that is what is most unknown */ /* Then our magic string */ /* Then the raw salt
    m = md5()
    m.update(password + magic + salt)

    # /* Then just as many characters of the MD5(pw, salt, pw) */
    mixin = md5(password + salt + password).digest()
    for i in range(0, len(password)):
        m.update(mixin[i % 16])

        # /* Then something really weird... */
        # Also really broken, as far as I can tell.    -m
        i = len(password)
    while i:
        if i & 1:
            m.update('\x00')
        else:
            m.update(password[0])
        i >>= 1

    final = m.digest()

    # /* and now, just to make sure things don't run too fast */
    for i in range(1000):
        m2 = md5()
        if i & 1:
            m2.update(password)
        else:
            m2.update(final)

        if i % 3:
            m2.update(salt)

        if i % 7:
            m2.update(password)

        if i & 1:
            m2.update(final)
        else:
            m2.update(password)

        final = m2.digest()

    # This is the bit that uses to64() in the original code.

    itoa64 = './0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'

    rearranged = ''
    for a, b, c in ((0, 6, 12), (1, 7, 13), (2, 8, 14), (3, 9, 15), (4, 10, 5)):
        v = ord(final[a]) << 16 | ord(final[b]) << 8 | ord(final[c])
        for i in range(4):
            rearranged += itoa64[v & 0x3f]
            v >>= 6

    v = ord(final[11])
    for i in range(2):
        rearranged += itoa64[v & 0x3f]
        v >>= 6

    return magic + salt + '$' + rearranged


if __debug__:
    rfc2307_tests = [
        # Test data generated by slappasswd of OpenLDAP 2.0.11
        ('test1', '{MD5}WhBei51A4TKXgNYuoiZdig=='),
        ('test1', '{SMD5}i1GhUWtlHIva18fyzSVoSi6pLqk='),
        ('test1', '{SHA}tESsBmE/yNY3lb6a0L6vVQEZNqw='),
        ('test1', '{SSHA}uWg1PmLHZsZUqGOncZBiRTNXE3uHSyGC'),
        ('test2', '{MD5}rQI0gpIFuQMxlrqBj3qHKw=='),
        ('test2', '{SMD5}cavgPXL7OAX6Nkz4oxPCw0ff8/8='),
        ('test2', '{SHA}EJ9LPFDXsN9ynSmbxvjp75Bmlx8='),
        ('test2', '{SSHA}STa8xdUq+G6StaVHCjAKzy0rB9DZBIry'),
        ('test3', '{MD5}ith1e6qFZNwTbB4HUH9KmA=='),
        ('test3', '{SMD5}MSQjqRuAZYtVmF1te6hO2Yn7gFQ='),
        ('test3', '{SHA}Pr+jAdxZGW8YWTxF5RkoeiMpdYk='),
        ('test3', '{SSHA}BUTK//6laPB9HN4cjK31RzTnmwMYmHnG'),
        ('test4', '{MD5}hpheEF95uV1ryRj7Rex3Jw=='),
        ('test4', '{SMD5}5TWxU4fGloruSpD0u1IdxKd5ZZA='),
        ('test4', '{SHA}H/KzcErt4E7stR5QymmO/VChN5s='),
        ('test4', '{SSHA}4ckBH1ib1IgiISp3tvZf4bDXtk5xlUBy'),
        ('test5', '{MD5}49cE81QrRKYh6+1w3A7+Ew=='),
        ('test5', '{SMD5}4NJzKqIX2sr8q3a4u0i92/4KPOY='),
        ('test5', '{SHA}kR3cO4+aE7VJm2vEY4orTz9ovyM='),
        ('test5', '{SSHA}kNTfeXHKb32yT4wUkN3AcpMCTHEx3Q2Q'),
        ('test6', '{MD5}TPrXB2Epli7nDDaDmh4+FQ=='),
        ('test6', '{SMD5}TesgPJdimK4miVwRcRQk/FZr7Uk='),
        ('test6', '{SHA}pm3yYRILbCMRxu8LG6tOWDr8vMA='),
        ('test6', '{SSHA}dIXzm4t40GfUXdHyBs//O3f09i/Ft3ik'),
        ('test7', '{MD5}sECD5T4kJiZZXiuOoyflJQ=='),
        ('test7', '{SMD5}TX6YHy6c0p1U9n6etx/irMv3cyE='),
        ('test7', '{SHA}6jJDEy1lOzkCWpROcPPs33DuOZQ='),
        ('test7', '{SSHA}zQ1xCPfNJgeDahwzzCLjM05cMJjaCULJ'),
        ('test8', '{MD5}XkDQn6BSl4Gv0SVKQpE4Rw=='),
        ('test8', '{SMD5}6wNcr1crfhnTOmJj0oi4Ukc9/+o='),
        ('test8', '{SHA}0D+dNBlDkwGebRLXyUKCfr1pREM='),
        ('test8', '{SSHA}BnNwRej74F2NicyGggpTgWUajPenNvZa'),
        ('test9', '{MD5}c5lptTJGsscnhQ27NJDt5g=='),
        ('test9', '{SMD5}mJUntKUUqtO+FgO7pIreIAHW4tA='),
        ('test9', '{SHA}U9Ulg2zJbQiaWkIYtGT9pTL33r4='),
        ('test9', '{SSHA}LdF62OhXywwvY6DMOCVkO25hHGG5fIAA'),
        # Test data from Netscape's perlSHA demo on developer docs page
        ('abc', '{SHA}qZk+NkcGgWq6PiVxeFDCbJzQ2J0='),
        (
            'abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq',
            '{SHA}hJg+RBw70m66rkqh+VEp5eVGcPE='
        ),
    ]

    def test():
        u = UserPassword()
        for password, encoded_password in rfc2307_tests:
            print password, encoded_password
            if not u._compareSinglePassword(password, encoded_password):
                print 'Test failed:', password, encoded_password

    if __name__ == '__main__':
        test()


def create_password_hash(raw_password):
    return '{crypt}%s' % md5crypt(raw_password)
