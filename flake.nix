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
          python-tldap = mkPoetryApplication { projectDir = self; };
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