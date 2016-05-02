Release 0.3.18 (03 May 2016)
============================
* Update my email address.
* Remove dependancy on Django.
* Add tox tests.
* Use setuptools-scm for versiong.
* Fix documentation.
* Add changelog to documentation.


Release 0.3.17 (26 Apr, 2016)
=============================
* Unbreak tests by using Node directly from Django.


Release 0.3.16 (26 Apr, 2016)
=============================
* Ensure we install test schemas.


Release 0.3.15 (10 Jan, 2016)
=============================
* Bugs fixed.
* Split Debian packaging.


Release 0.3.14 (10 Nov, 2015)
=============================
* Don't include docs directory in package. Closes: #804643.


Release 0.3.13 (26 Oct, 2015)
=============================
* Ensure tests run for Python3.4 and Python3.5.


Release 0.3.13 (18 Oct, 2015)
=============================
* Fix FTBFS issues. Closes: #801943


Release 0.3.12 (24 Aug, 2015)
=============================
* Fix FTBFS issues. #796756.
* Update git repository location.


Release 0.3.11 (11 Jun, 2015)
=============================
* Fix ds389 account locking/unlocking.
* Define new LOCKED_ROLE setting for ds389.


Release 0.3.10 (20 Feb, 2015)
=============================
* Fix TLS configuration. Will break existing setups if validation fails.
* python3-ldap renamed to ldap3 upstream.


Release 0.3.9 (19 Feb, 2015)
=============================
* Various bug fixes.


Release 0.3.8 (18 Nov, 2014)
=============================
* Works with python3-ldap 0.9.6.2.
* Don't use depreciated django.utils.importlib.
* Update standards version to 3.9.6.


Release 0.3.7 (09 Sep, 2014)
=============================
* Add more read only attributes.
* Add Django 1.7 migration.


Release 0.3.6 (08 Sep, 2014)
=============================
* Rename migrations to south_migrations.
* Add groupOfNames objectClass.
* hasSubordinates is read only attribute.


Release 0.3.5 (07 Aug, 2014)
=============================
* Update override_dh_auto_test.
* Really fix debian/copyright file.


Release 0.3.4 (15 Jul, 2014)
=============================
* Don't die if default LDAP server not configured.


Release 0.3.3 (14 Jul, 2014)
============================
* Fix typo.
* Remove hard dependency on Django.
* Rename source project.
* Move ldap_passwd from tldap.methods.
* Fix Debian copyright.
* Retry upload to Debian. Closes: #753482.


Release 0.3.2 (09 Jul, 2014)
=============================
* Fix PEP8 issues.
* FIx close() undefined error, python-ldap3 0.9.4.2
* Trick pep8 into ignoring E721.
* Revert "Copy escape_bytes function from ldap3."


Release 0.3.1 (06 Jul, 2014)
============================
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


Release 0.3.0 (01 Jul, 2014)
============================
* Python3 support.
* Python3 package.


Release 0.2.17 (28 Mar, 2014)
=============================
* Replace USE_TLS setting with REQUIRE_TLS and START_TLS settings.
  Old USE_TLS setting will no longer work.


Release 0.2.16 (24 Mar, 2014)
=============================
* New release.
* Fix PEP8 style issues.
* Replace ldap_passwd with passlib code.
* Testing: check LDAP port not already in use.


Release 0.2.15 (11 Mar, 2014)
=============================
* Move tests to tldap.tests.
* Update Python packaging.
* Update documentation.


Release 0.2.14 (17 Feb, 2014)
=============================
* Support moving objects in LDAP tree.
* Fix replaces/breaks header for upgrades from legacy package.


Release 0.2.13 (05 Feb, 2014)
=============================
* Initial documentation.
* Make transactions operate on all connections by default.
* Remove obsolete functions.

Release 0.2.12 (28 Jan, 2014)
=============================
* Use dh_python2 for packaging.


Release 0.2.11 (21 Jan, 2014)
=============================
* Fix bug in samba specific function.
* Works with no LDAP servers configured.


Release 0.2.10 (17 Dec, 2013)
=============================
* Bug fixes.


Release 0.2.9 (14 Aug, 2013)
============================
* Update referenced backend names.
* Rewrite method functions.
* Fix creating gid and uid for different servers.
* Updates to 389 support.


Release 0.2.8 (26 Jul, 2013)
============================
* Rename backends.
  tldap.backend.transaction to tldap.backend.fake_transactions
  tldap.backend.python to tldap.backend.no_transactions
* Remove prefixes from LDAP names.


Release 0.2.7 (18 Jul, 2013)
============================
* New methods submodule, moved from placard schema.
* Add depends on python-ldap.
* Fix LDAP bind if connection failed.
* Fix md5-crypt password comparison.
* Write LDAP entries to ldif_writer.


Release 0.2.6 (27 May, 2013)
============================
* Tests: Purge environment when calling slapd.
* Update description to reflect what tldap does.


Release 0.2.5 (01 May, 2013)
============================
* Support new method of creating schemas.


Release 0.2.4 (22 Mar, 2013)
============================
* Add classes that were deleted in error.


Release 0.2.3 (15 Mar, 2013)
============================
* Fix copy of CaseInsensitiveDict.
* PEP8 formatting fixed.


Release 0.2.2 (19 Feb, 2013)
============================
* Fix bug in processing commit flag.


Release 0.2.1 (18 Feb, 2013)
============================
* Fix tests.


Release 0.2 (08 Feb, 2013)
==========================
* Lots and lots and lots of updates.


Release 0.1 (03 Apr, 2012)
==========================
* Initial release.
