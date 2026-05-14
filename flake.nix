{
  description = "Nix flake for stryktips Python development";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils, ... }: flake-utils.lib.eachDefaultSystem (system:
    let
      pkgs = import nixpkgs { inherit system; };
      pythonEnv = pkgs.python314.withPackages (ps: with ps; [ pip setuptools wheel pytest ]);
    in {
      devShells.default = pkgs.mkShell {
        buildInputs = [
          pythonEnv
          pkgs.python314Packages.black
          pkgs.python314Packages.ruff
          pkgs.python314Packages.mypy
          pkgs.python314Packages.ipython
        ];

        shellHook = ''
          echo "Python development shell ready. Use python, pytest, black, ruff, mypy, ipython."
        '';
      };
    }
  );
}
