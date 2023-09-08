{
  description = "Python LDAP library";

  inputs.flake-utils.url = "github:numtide/flake-utils";
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-23.05";
  inputs.poetry2nix = {
    url = "github:nix-community/poetry2nix";
    inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs = { self, nixpkgs, flake-utils, poetry2nix }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        # see https://github.com/nix-community/poetry2nix/tree/master#api for more functions and examples.
        inherit (poetry2nix.legacyPackages.${system}) mkPoetryApplication;
        pkgs = nixpkgs.legacyPackages.${system};
        slapd = pkgs.writeShellScriptBin "slapd" ''
          exec ${pkgs.openldap}/libexec/slapd "$@"
        '';

      in {
        packages = {
          python-tldap = mkPoetryApplication {
            projectDir = self;
            overrides = pkgs.poetry2nix.overrides.withDefaults (self: super: {
              # See https://github.com/nix-community/poetry2nix/issues/1184
              pip = pkgs.python3.pkgs.pip;
              # See https://github.com/nix-community/poetry2nix/issues/413
              cryptography = super.cryptography.overridePythonAttrs (old: {
                cargoDeps = pkgs.rustPlatform.fetchCargoTarball {
                  src = old.src;
                  sourceRoot = "${old.pname}-${old.version}/src/rust";
                  name = "${old.pname}-${old.version}";
                  # This is what we actually want to patch.
                  sha256 = pkgs.lib.fakeSha256;
                };
              });
            });
          };
          default = self.packages.${system}.python-tldap;
        };

        devShells.default = pkgs.mkShell {
          packages = [
            poetry2nix.packages.${system}.poetry
            pkgs.libffi
            slapd
            pkgs.openldap
          ];
        };
      });
}
