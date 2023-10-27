{
  description = "Python LDAP library";

  inputs.flake-utils.url = "github:numtide/flake-utils";
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-23.05";
  inputs.poetry2nix = {
    # url = "github:nix-community/poetry2nix";
    url = "github:sciyoshi/poetry2nix/new-bootstrap-fixes";
    inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs = { self, nixpkgs, flake-utils, poetry2nix }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        p2n = import poetry2nix { inherit pkgs; };
        mkPoetryApplication = p2n.mkPoetryApplication;
        pkgs = nixpkgs.legacyPackages.${system};
        slapd = pkgs.writeShellScriptBin "slapd" ''
          exec ${pkgs.openldap}/libexec/slapd "$@"
        '';

      in {
        packages = {
          python-tldap = mkPoetryApplication {
            projectDir = self;
            # See https://github.com/nix-community/poetry2nix/issues/1184
            overrides = pkgs.poetry2nix.overrides.withDefaults
              (self: super: { pip = pkgs.python3.pkgs.pip; });
          };
          default = self.packages.${system}.python-tldap;
        };

        devShells.default = pkgs.mkShell {
          packages = [ pkgs.poetry pkgs.libffi slapd pkgs.openldap ];
        };
      });
}
