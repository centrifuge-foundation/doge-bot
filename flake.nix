{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    nix-utils.url = "github:numtide/flake-utils";
    nix-filter.url = "github:numtide/nix-filter";
  };

  outputs = { self, nixpkgs, nix-utils, nix-filter }:
    nix-utils.lib.eachDefaultSystem (system:
      with import nixpkgs { inherit system; };
      let
        projectFiles = nix-filter.lib {
          root = ./.;
          include = (map nix-filter.lib.inDirectory [ "roombot" ])
            ++ [ "maubot.yaml" "poetry.lock" "pyproject.toml" ];
        };
        pythonWithPackages = pkgs.poetry2nix.mkPoetryEnv {
          projectDir = ./.;
          preferWheels = true;
        };
      in {
        devShell = pkgs.mkShell {
          buildInputs = with pkgs; [
            pythonWithPackages
            python3Packages.poetry
          ];
        };
        defaultPackage = writeShellScriptBin "roombot" ''
          ${pythonWithPackages}/bin/python -m maubot.standalone \
            --meta ${projectFiles}/maubot.yaml "$@"
        '';
        defaultApp =
          nix-utils.lib.mkApp { drv = self.defaultPackage."${system}"; };
      });
}
