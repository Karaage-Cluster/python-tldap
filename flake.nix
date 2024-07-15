{
  description = "Python LDAP library";

  inputs.flake-utils.url = "github:numtide/flake-utils";
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-24.05";
  inputs.poetry2nix = {
    url = "github:nix-community/poetry2nix";
    # url = "github:sciyoshi/poetry2nix/new-bootstrap-fixes";
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
            overrides = p2n.overrides.withDefaults (final: prev: {
              nh3 = prev.nh3.override { preferWheel = true; };
              furo = prev.furo.override { preferWheel = true; };
              bump2version = prev.bump2version.overridePythonAttrs (oldAttrs: {
                buildInputs = oldAttrs.buildInputs ++ [ final.setuptools ];
              });
            });
          };
          default = self.packages.${system}.python-tldap;
        };

        devShells.default = pkgs.mkShell {
          packages = [ pkgs.poetry pkgs.libffi slapd pkgs.openldap ];
        };
      });
}
