"""
Utilities for starting up a test slapd server
and talking to it with ldapsearch/ldapadd.
"""
import base64
import logging
import os
import socket
import subprocess
import sys
import tempfile
import time
from typing import Dict, List, Optional, Tuple

import tldap.ldap_passwd as lp


_log = logging.getLogger("slapd")


def quote(s: str) -> str:
    """
    Quotes the '"' and '\' characters in a string and surrounds with "..."
    """
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'


def mkdirs(path: str) -> str:
    """Creates the directory path unless it already exists"""
    if not os.access(os.path.join(path, os.path.curdir), os.F_OK):
        _log.debug("creating temp directory %s", path)
        os.mkdir(path)
    return path


def delete_directory_content(path: str) -> None:
    for dirpath, dirnames, filenames in os.walk(path, topdown=False):
        for n in filenames:
            _log.info("remove %s", os.path.join(dirpath, n))
            os.remove(os.path.join(dirpath, n))
        for n in dirnames:
            _log.info("rmdir %s", os.path.join(dirpath, n))
            os.rmdir(os.path.join(dirpath, n))


LOCALHOST = '127.0.0.1'


def is_port_in_use(port: int, host: str = LOCALHOST) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex((host, int(port)))
    sock.close()
    if result == 0:
        return True
    return False


def find_available_tcp_port(host: str = LOCALHOST) -> int:
    s = socket.socket()
    s.bind((host, 0))
    port = s.getsockname()[1]
    s.close()
    _log.info("Found available port %d", port)
    return port


class Slapd:
    """
    Controller class for a slapd instance, OpenLDAP's server.

    This class creates a temporary data store for slapd, runs it
    on a private port, and initialises it with a top-level dc and
    the root user.

    When a reference to an instance of this class is lost, the slapd
    server is shut down.
    """

    _log = logging.getLogger("Slapd")

    # Use /var/tmp to placate apparmour on Ubuntu:
    TEST_UTILS_DIR = os.path.abspath(os.path.split(__file__)[0])
    PATH_SCHEMA_DIR = TEST_UTILS_DIR + "/ldap_schemas/"
    PATH_LDAPADD = "ldapadd"
    PATH_LDAPSEARCH = "ldapsearch"
    PATH_SLAPD = "slapd"
    PATH_SLAP_TEST = "slaptest"

    def __init__(self) -> None:
        self._proc = None
        self._proc_config: Optional[str] = None
        self._port: int = 0
        self._tmpdir: Optional[str] = None
        self._dn_suffix: str = "dc=python-ldap,dc=org"
        self._root_cn: str = "Manager"
        self._root_password: str = "password"
        self._slapd_debug_level: int or str = 0
        self._env: Dict[str, str] = {
            'PATH': os.getenv('PATH')
        }

    # Setters
    def set_port(self, port: int) -> None:
        self._port = port

    def set_dn_suffix(self, dn: str) -> None:
        self._dn_suffix = dn

    def set_root_cn(self, cn: str) -> None:
        self._root_cn = cn

    def set_root_password(self, pw: str) -> None:
        self._root_password = pw

    def set_slapd_debug_level(self, level: int or str) -> None:
        self._slapd_debug_level = level

    def set_debug(self) -> None:
        self._log.setLevel(logging.DEBUG)
        self.set_slapd_debug_level('Any')

    # getters
    def get_url(self) -> str:
        return "ldap://%s:%d/" % self.get_address()

    def get_address(self) -> Tuple[str, int]:
        if self._port == 0:
            self._port = find_available_tcp_port(LOCALHOST)
        return LOCALHOST, self._port

    def get_dn_suffix(self) -> str:
        return self._dn_suffix

    def get_root_dn(self) -> str:
        return "cn=" + self._root_cn + "," + self.get_dn_suffix()

    def get_root_password(self) -> str:
        return self._root_password

    def _setup_tmp_dir(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        ldif_dir = mkdirs(os.path.join(self._tmpdir, "ldif-data"))
        delete_directory_content(ldif_dir)  # clear it out

        self._proc_config = os.path.join(self._tmpdir, "slapd.conf")

    def _configure(self) -> List[str]:
        """
        Appends slapd.conf configuration lines to cfg.
        Also re-initializes any backing storage.
        Feel free to subclass and override this method.
        """
        ldif_dir = os.path.join(self._tmpdir, "ldif-data")

        cfg = []

        # Global
        schema_list = os.listdir(self.PATH_SCHEMA_DIR)
        schema_list.sort()
        for schema in schema_list:
            cfg.append("include " + quote(self.PATH_SCHEMA_DIR + schema))

        cfg.append("allow bind_v2")

        # Database
        cfg.append("moduleload back_mdb")
        cfg.append("moduleload ppolicy")
        cfg.append('')

        cfg.append("database mdb")
        cfg.append("directory " + quote(ldif_dir))

        cfg.append("suffix " + quote(self.get_dn_suffix()))
        cfg.append("overlay ppolicy")
        cfg.append(f'ppolicy_default {quote("cn=default,"+self.get_dn_suffix())}')
        cfg.append("# rootdn " + quote(self.get_root_dn()))
        cfg.append("# rootpw " + quote(
            lp.encode_password(self.get_root_password())))
        cfg.append('')

        cfg.append(f'access to dn.sub={quote(self.get_dn_suffix())} attrs=userPassword')
        cfg.append('   by anonymous auth')
        cfg.append('')

        cfg.append(f'access to dn.sub={quote(self.get_dn_suffix())}')
        cfg.append(f'   by dn.exact={quote(self.get_root_dn())} write')
        cfg.append('')

        return cfg

    def _write_config(self) -> None:
        """Writes the slapd.conf file out, and returns the path to it."""
        cfg = self._configure()
        path = self._proc_config

        mkdirs(self._tmpdir)
        if os.access(path, os.F_OK):
            self._log.debug("deleting existing %s", path)
            os.remove(path)
        self._log.debug("writing config to %s", path)
        f = open(path, "w")
        f.writelines([line + "\n" for line in cfg])
        f.close()

    def _populate(self) -> None:
        suffix_dc = self.get_dn_suffix().split(',')[0][3:]
        root_cn = self.get_root_dn().split(',')[0][3:]

        p = os.path.join(self._tmpdir, "admin.ldif")
        with open(p, "w") as f:
            f.write(f"dn: {self.get_dn_suffix()}\n")
            f.write(f"dc: {suffix_dc}\n")
            f.write(f"o: {suffix_dc}\n")
            f.write("objectClass: dcObject\n")
            f.write("objectClass: organization\n")
            f.write("\n")
            f.write(f"dn: {self.get_root_dn()}\n")
            f.write(f"cn: {root_cn}\n")
            f.write("objectClass: simpleSecurityObject\n")
            f.write("objectClass: organizationalRole\n")
            f.write(f"userPassword: {lp.encode_password(self.get_root_password())}\n")
            f.write("\n")
            f.write(f'dn: cn=default,{self.get_dn_suffix()}\n')
            f.write('objectClass: top\n')
            f.write('objectClass: device\n')
            f.write('objectClass: pwdPolicy\n')
            f.write('pwdAttribute: userPassword\n')
            f.write('pwdLockout: TRUE\n')
            f.write("\n")
            f.write(f'dn: ou=People,{self.get_dn_suffix()}\n')
            f.write('objectClass: top\n')
            f.write('objectClass: OrganizationalUnit\n')
            f.write('ou: People\n')
            f.write("\n")
            f.write(f'dn: ou=Groups,{self.get_dn_suffix()}\n')
            f.write('objectClass: top\n')
            f.write('objectClass: OrganizationalUnit\n')
            f.write('ou: Groups\n')

        config_path = os.path.join(self._tmpdir, "slapd.conf")
        subprocess.check_call(["slapadd", "-n", "1", "-f", config_path, "-l", p])

    def start(self) -> None:
        """
        Starts the slapd server process running, and waits for it to come up.
        """
        if self._proc is None:
            ok = False
            try:
                self._setup_tmp_dir()
                self._write_config()
                self._populate()
                self._test_configuration()
                if is_port_in_use(self._port):
                    raise Exception('Port %s is already in use' % self._port)
                self._start_slapd()
                self._wait_for_slapd()
                ok = True
                self._log.debug("slapd ready at %s", self.get_url())
            finally:
                if not ok:
                    if self._proc:
                        self.stop()

    def _start_slapd(self) -> None:
        # Spawns/forks the slapd process
        self._log.info("starting slapd")
        self._proc = subprocess.Popen([
            self.PATH_SLAPD,
            "-f", self._proc_config,
            "-h", self.get_url(),
            "-d", str(self._slapd_debug_level),
        ], env=self._env)

    def _wait_for_slapd(self) -> None:
        # Waits until the LDAP server socket is open, or slapd crashed
        s = socket.socket()
        while 1:
            if self._proc.poll() is not None:
                self._stopped()
                raise RuntimeError("slapd exited before opening port")
            try:
                self._log.debug("Connecting to %s", repr(self.get_address()))
                s.connect(self.get_address())
                s.close()
                return
            except socket.error:
                time.sleep(1)

    def stop(self) -> None:
        """Stops the slapd server, and waits for it to terminate"""
        if self._proc is not None:
            self._log.debug("stopping slapd")
            if hasattr(self._proc, 'terminate'):
                self._proc.terminate()
            else:
                import posix
                import signal
                posix.kill(self._proc.pid, signal.SIGHUP)
                # time.sleep(1)
                # posix.kill(self._proc.pid, signal.SIGTERM)
                # posix.kill(self._proc.pid, signal.SIGKILL)
            self.wait()

    def restart(self) -> None:
        """
        Restarts the slapd server; ERASING previous content.
        Starts the server even it if isn't already running.
        """
        self.stop()
        self.start()

    def wait(self) -> None:
        """Waits for the slapd process to terminate by itself."""
        if self._proc:
            self._proc.wait()
            self._stopped()

    def _stopped(self) -> None:
        """Called when the slapd server is known to have terminated"""
        if self._proc is not None:
            self._log.info("slapd terminated")
            self._proc = None
            self._proc_config = None
        if self._tmpdir is not None:
            import shutil
            shutil.rmtree(self._tmpdir)
            self._tmpdir = None

    def _test_configuration(self) -> None:
        self._log.debug("testing configuration")
        verbose_flag = "-Q"
        if self._log.isEnabledFor(logging.DEBUG):
            verbose_flag = "-v"
        p = subprocess.Popen(
            [
                self.PATH_SLAP_TEST,
                verbose_flag,
                "-f", self._proc_config,
            ], env=self._env)
        if p.wait() != 0:
            raise RuntimeError("configuration test failed")
        self._log.debug("configuration seems ok")

    def ldap_add(self, ldif: str, extra_args: Optional[List] = None) -> None:
        """Runs ldapadd on this slapd instance, passing it the ldif content"""
        if extra_args is None:
            extra_args = []
        self._log.debug("adding %s", repr(ldif))
        p = subprocess.Popen([
            self.PATH_LDAPADD,
            "-x",
            "-D", self.get_root_dn(),
            "-w", self.get_root_password(),
            "-H", self.get_url()] + extra_args,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            env=self._env)
        p.communicate(ldif.encode("utf_8"))
        if p.wait() != 0:
            raise RuntimeError("ldapadd process failed")

    def ldap_search(self, base: Optional[str] = None,
                    filter: str = '(objectClass=*)',
                    attrs: Optional[List[str]] = None,
                    scope: str = 'sub',
                    extra_args: Optional[List[str]] = None):
        if base is None:
            base = self.get_dn_suffix()
        if attrs is None:
            attrs = []
        if extra_args is None:
            extra_args = []
        self._log.debug("ldapsearch filter=%s", repr(filter))
        p = subprocess.Popen([
            self.PATH_LDAPSEARCH,
            "-x",
            "-D", self.get_root_dn(),
            "-w", self.get_root_password(),
            "-H", self.get_url(),
            "-b", base,
            "-s", scope,
            "-LL", ] + extra_args + [filter] + attrs,
            stdout=subprocess.PIPE,
            env=self._env)
        output = p.communicate()[0]
        if p.wait() != 0:
            raise RuntimeError("ldapadd process failed")

        # RFC 2849: LDIF format
        # unfold
        lines = []
        output = output.decode("utf_8")
        for line in output.split('\n'):
            if line.startswith(' '):
                lines[-1] = lines[-1] + line[1:]
            elif line == '' and lines and lines[-1] == '':
                pass  # ignore multiple blank lines
            else:
                lines.append(line)
        # Remove comments
        lines = [line for line in lines if not line.startswith("#")]

        # Remove leading version and blank line(s)
        if lines and lines[0] == '':
            del lines[0]
        if not lines or lines[0] != 'version: 1':
            raise RuntimeError("expected 'version: 1', got " + repr(lines[:1]))
        del lines[0]
        if lines and lines[0] == '':
            del lines[0]

        # ensure the ldif ends with a blank line (unless it is just blank)
        if lines and lines[-1] != '':
            lines.append('')

        objects = []
        obj = []
        for line in lines:
            if line == '':  # end of an object
                if obj[0][0] != 'dn':
                    raise RuntimeError("first line not dn", repr(obj))
                objects.append((obj[0][1], obj[1:]))
                obj = []
            else:
                attr, value = line.split(':', 2)
                if value.startswith(': '):
                    value = base64.decodebytes(value[2:])
                elif value.startswith(' '):
                    value = value[1:]
                else:
                    raise RuntimeError("bad line: " + repr(line))
                obj.append((attr, value))
        assert obj == []
        return objects


def test() -> None:
    logging.basicConfig(level=logging.DEBUG)
    slapd = Slapd()
    try:
        print("Starting slapd...")
        slapd.start()

        print("Contents of LDAP server follow:\n")
        for dn, attrs in slapd.ldap_search():
            print("dn: " + dn)
            for name, val in attrs:
                print(name + ": " + val)
            print("")

        if len(sys.argv) > 1:
            args = sys.argv[1:]
            env = {
                **os.environ,
                'LDAP_TYPE': "openldap",
                'LDAP_URL': slapd.get_url(),
                'LDAP_DN': slapd.get_root_dn(),
                'LDAP_PASSWORD': slapd.get_root_password(),
                'LDAP_ACCOUNT_BASE':  f"ou=People,{slapd.get_dn_suffix()}",
                'LDAP_GROUP_BASE':  f"ou=Groups,{slapd.get_dn_suffix()}",
            }
            print(f"Running command {args}...")
            subprocess.check_call(args, env=env)

        print("Contents of LDAP server follow:\n")
        for dn, attrs in slapd.ldap_search():
            print("dn: " + dn)
            for name, val in attrs:
                print(name + ": " + val)
            print("")
    finally:
        slapd.stop()


if __name__ == '__main__':
    test()
