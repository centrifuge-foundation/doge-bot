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
        poetryEnv = poetry2nix.mkPoetryEnv {
          projectDir = ./.;
          python = python39;
          preferWheels = true;
        };
        pythonModule = poetry2nix.mkPoetryApplication {
          projectDir = ./.;
          python = python39;
          preferWheels = true;
        };
        pythonWithPackages = poetryEnv.withPackages (ps: [ pythonModule ]);
      in rec {
        devShell = poetryEnv.env.overrideAttrs
          (oldAttrs: { buildInputs = [ poetry jq ]; });

        defaultPackage = writeShellScriptBin "doge-bot" ''
          ${pythonWithPackages}/bin/python -m maubot.standalone -m ${
            ./maubot.yaml
          } "$@"
        '';

        packages.docker = dockerTools.buildLayeredImage {
          name = "doge-bot";
          contents = [ pythonWithPackages cacert ];
          config = {
            Env = [ "NIX_SSL_CERT_FILE=/etc/ssl/certs/ca-bundle.crt" ];
            Cmd = [ "python" "-m" "maubot.standalone" "-m" ./maubot.yaml ];
            WorkingDir = "/data";
            Volumes = { "/data" = { }; };
          };
          tag = "latest";
        };

        defaultApp =
          nix-utils.lib.mkApp { drv = self.defaultPackage."${system}"; };
      });
}
