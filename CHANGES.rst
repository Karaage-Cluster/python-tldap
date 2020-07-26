==========
Change log
==========
All notable changes to this project will be documented in this file. The format
is based on `Keep a Changelog`_ and this project
adheres to `Semantic Versioning`_.

.. _`Keep a Changelog`: http://keepachangelog.com/
.. _`Semantic Versioning`: http://semver.org/


UNRELEASED
----------

Changed
~~~~~~~
* Bump dependancies for testing.


1.0.3 - 2019-03-06
------------------

Changed
~~~~~~~
* Use circleci for builds.


1.0.2 - 2019-02-19
------------------

Fixed
~~~~~
* Ensure get_and_increment is run in transaction.
* Give Django app sensible short name.
* Pass database parameter as required in load() method.


1.0.1 - 2018-12-03
------------------

Fixed
~~~~~
* Add missing tldap.django package.


1.0.0 - 2018-12-03
------------------

Changed
~~~~~~~
* Complete rewrite/simplification of API.
* Not compatible with previous versions.


0.4.4 - 2018-03-02
------------------

Changed
~~~~~~~
* Django middleware now inherits from django.utils.deprecation.MiddlewareMixin
* Update pytest requirement.


0.4.3 - 2018-02-13
------------------
Forgot to merge master before releasing 0.4.2; retry.


0.4.2 - 2018-02-13
------------------

Changed
~~~~~~~
* Updated requirements.
* Changed filter string to byte string.

Removed
~~~~~~~
* Python 3.5 support.


0.4.1 - 2017-05-01
------------------

Fixed
~~~~~
* Remove unused dependancy on pytest-mock.
* Added upload information to setup.cfg


0.4.0 - 2017-05-01
------------------
Increment minor version as we changed the default password hash to a new one
that isn't supported by earlier versions of TLDAP.

Added
~~~~~
* Supports ldap3 2.2.3

Changed
~~~~~~~
* Rewrote test cases. Now smaller in scope for what each test covers. Needs
  more work for queries.

Fixed
~~~~~
* Fixed bug setting primary group if primary group already set.
* Allow clearing/setting primary group if current value invalid.
* Fix incorrect DN calculated in cached data after move.

Security
~~~~~~~~
* Use sha512_crypt by default for passwords instead of ldap_salted_sha1. We
  still support salted ldap_salted_sha1 for existing passwords.


0.3.20 - 2017-04-21
-------------------

Deprecated
~~~~~~~~~~
* Remove setuptools_scm/readthedocs hack.

Fixed
~~~~~
* Remove registeredAddresss attribute which is undefined in OpenLDAP.


0.3.19 - 2017-04-21
-------------------
Changes to work with latest software. Note that ldap3 >= 2 still has
problems that are being worked on. Also we get warnings that the
`encode` method in passlib has been replaced by the `hash` method.

Added
~~~~~
* Python 3.6 support.
* No longer depends on Django. Django support is optional.

Deprecated
~~~~~~~~~~
* Python 3.3 support.

Fixed
~~~~~
* Include ``version.py`` on PyPi source.
* Use ``requirements.txt`` to declare knowed good versions of
  software we depend on.
* Update ``90-ppolicy.schema`` to work with latest slapd.
* Various updates to fix problems with ldap3 >= 2.
* Fix PEP8 errors.
* Fix `verbose_name` undefined error.
* Fix name of project in documentation.


0.3.18 - 2016-05-03
-------------------
* Update my email address.
* Remove dependancy on Django.
* Add tox tests.
* Use setuptools-scm for versiong.
* Fix documentation.
* Add changelog to documentation.


0.3.17 - 2016-04-26
-------------------
* Unbreak tests by using Node directly from Django.


0.3.16 - 2016-04-26
-------------------
* Ensure we install test schemas.


0.3.15 - 2016-01-10
-------------------
* Bugs fixed.
* Split Debian packaging.


0.3.14 - 2015-11-10
-------------------
* Don't include docs directory in package. Closes: #804643.


0.3.13 - 2015-10-26
-------------------
* Ensure tests run for Python3.4 and Python3.5.


0.3.13 - 2015-10-18
-------------------
* Fix FTBFS issues. Closes: #801943


0.3.12 - 2015-08-24
-------------------
* Fix FTBFS issues. #796756.
* Update git repository location.


0.3.11 - 2015-06-11
-------------------
* Fix ds389 account locking/unlocking.
* Define new LOCKED_ROLE setting for ds389.


0.3.10 - 2015-02-20
-------------------
* Fix TLS configuration. Will break existing setups if validation fails.
* python3-ldap renamed to ldap3 upstream.


0.3.9 - 2015-02-19
------------------
* Various bug fixes.


0.3.8 - 2014-11-18
------------------
* Works with python3-ldap 0.9.6.2.
* Don't use depreciated django.utils.importlib.
* Update standards version to 3.9.6.


0.3.7 - 2014-09-09
------------------
* Add more read only attributes.
* Add Django 1.7 migration.


0.3.6 - 2014-09-08
------------------
* Rename migrations to south_migrations.
* Add groupOfNames objectClass.
* hasSubordinates is read only attribute.


0.3.5 - 2014-08-07
-------------------
* Update override_dh_auto_test.
* Really fix debian/copyright file.


0.3.4 - 2014-07-15
------------------
* Don't die if default LDAP server not configured.


0.3.3 - 2014-07-14
------------------
* Fix typo.
* Remove hard dependency on Django.
* Rename source project.
* Move ldap_passwd from tldap.methods.
* Fix Debian copyright.
* Retry upload to Debian. Closes: #753482.


0.3.2 - 2014-07-09
-------------------
* Fix PEP8 issues.
* FIx close() undefined error, python-ldap3 0.9.4.2
* Trick pep8 into ignoring E721.
* Revert "Copy escape_bytes function from ldap3."


0.3.1 - 2014-07-06
------------------
* Add link to homepage.
* Remove unneeded file.
* New release for Debian.
* Add Vcs headers.
* Declare Python 3 compatible.
* Fix __unicode__ string methods for Python 3.
* Don't connect to LDAP until we need to.
* Python 3 tests.
* PEP8 fixes.
* Run flake8 tests during build.


0.3.0 - 2014-07-01
------------------
* Python3 support.
* Python3 package.


0.2.17 - 2014-03-28
-------------------
* Replace USE_TLS setting with REQUIRE_TLS and START_TLS settings.
  Old USE_TLS setting will no longer work.


0.2.16 - 2014-03-24
-------------------
* New release.
* Fix PEP8 style issues.
* Replace ldap_passwd with passlib code.
* Testing: check LDAP port not already in use.


0.2.15 - 2014-03-11
-------------------
* Move tests to tldap.tests.
* Update Python packaging.
* Update documentation.


0.2.14 - 2014-02-17
-------------------
* Support moving objects in LDAP tree.
* Fix replaces/breaks header for upgrades from legacy package.


0.2.13 - 2014-02-05
-------------------
* Initial documentation.
* Make transactions operate on all connections by default.
* Remove obsolete functions.

0.2.12 - 2014-01-28
-------------------
* Use dh_python2 for packaging.


0.2.11 - 2014-01-21
-------------------
* Fix bug in samba specific function.
* Works with no LDAP servers configured.


0.2.10 - 2013-12-17
-------------------
* Bug fixes.


0.2.9 - 2013-08-14
------------------
* Update referenced backend names.
* Rewrite method functions.
* Fix creating gid and uid for different servers.
* Updates to 389 support.


0.2.8 - 2013-07-26
------------------
* Rename backends.
  tldap.backend.transaction to tldap.backend.fake_transactions
  tldap.backend.python to tldap.backend.no_transactions
* Remove prefixes from LDAP names.


0.2.7 - 2013-07-18
------------------
* New methods submodule, moved from placard schema.
* Add depends on python-ldap.
* Fix LDAP bind if connection failed.
* Fix md5-crypt password comparison.
* Write LDAP entries to ldif_writer.


0.2.6 - 2013-05-27
------------------
* Tests: Purge environment when calling slapd.
* Update description to reflect what tldap does.


0.2.5 - 2013-05-01
------------------
* Support new method of creating schemas.


0.2.4 - 2013-03-22
------------------
* Add classes that were deleted in error.


0.2.3 - 2013-03-15
------------------
* Fix copy of CaseInsensitiveDict.
* PEP8 formatting fixed.


0.2.2 - 2013-02-19
------------------
* Fix bug in processing commit flag.


0.2.1 - 2013-02-18
------------------
* Fix tests.


0.2 - 2013-02-08
----------------
* Lots and lots and lots of updates.


0.1 - 2012-04-03
----------------
* Initial release.
