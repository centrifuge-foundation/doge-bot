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
        poetryEnv = pkgs.poetry2nix.mkPoetryEnv {
          projectDir = ./.;
          python = python39;
          preferWheels = true;
        };
      in rec {
        devShell = poetryEnv.env.overrideAttrs (oldAttrs: { 
          buildInputs = [ pkgs.poetry ]; 
        });

        defaultPackage = writeShellScriptBin "doge-bot" ''
          ${poetryEnv}/bin/python -m maubot.standalone -m ${./maubot.yaml} "$@"
        '';

        packages.docker = let
          package = pkgs.poetry2nix.mkPoetryApplication {
            projectDir = ./.;
            python = pkgs.python39;
            preferWheels = true;
          };
          pythonWithPackages = poetryEnv.withPackages (ps: [ package ]);
        in pkgs.dockerTools.buildLayeredImage {
          name = "doge-bot";
          contents = [ pythonWithPackages ];
          config.Entrypoint =
            [ "python" "-m" "maubot.standalone" "-m" ./maubot.yaml ];
          tag = "latest";
        };

        defaultApp =
          nix-utils.lib.mkApp { drv = self.defaultPackage."${system}"; };
      });
}
