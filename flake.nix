{
  description = "Nix flake for stryktips Python development";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-24.11";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils, ... }: flake-utils.lib.eachDefaultSystem (system:
    let
      pkgs = import nixpkgs { inherit system; };
      pythonEnv = pkgs.python311.withPackages (ps: with ps; [ pip setuptools wheel pytest ]);
    in {
      devShells.default = pkgs.mkShell {
        buildInputs = [
          pythonEnv
          pkgs.python311Packages.black
          pkgs.python311Packages.ruff
          pkgs.python311Packages.mypy
          pkgs.python311Packages.ipython
        ];

        shellHook = ''
          echo "Python development shell ready. Use python, pytest, black, ruff, mypy, ipython."
        '';
      };
    }
  );
}
