{ pkgs ? import <nixpkgs> {} }:

let
  led-matrix-monitoring = pkgs.callPackage ./default.nix {};
in
pkgs.mkShell {
  buildInputs = [
    led-matrix-monitoring
  ];
}

