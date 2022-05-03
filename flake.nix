{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, utils }:
    let
      out = system:
        let pkgs = nixpkgs.legacyPackages."${system}";
        in {

          # devShell = pkgs.mkShell {
          #     buildInputs = with pkgs; [
          #         python3Packages.poetry
          #     ];
          # };
          devShell = with pkgs.poetry2nix;
            mkPoetryApplication {
              projectDir = ./.;
              overrides = pkgs.poetry2nix.overrides.withDefaults (self: super: {
                pyparsing = super.pyparsing.overridePythonAttrs (old: {
                  buildInputs = old.buildInputs ++ [ self.flit-core ];
                });
              });
              # editablePackageSources = { my-app = ./src; };
            };

          defaultPackage = with pkgs.poetry2nix;
            mkPoetryApplication {
              projectDir = ./.;
              preferWheels = true;
            };

          defaultApp =
            utils.lib.mkApp { drv = self.defaultPackage."${system}"; };

        };
    in with utils.lib; eachSystem defaultSystems out;

}
