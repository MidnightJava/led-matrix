{
  description = "LED Matrix Monitoring application for Framework 16";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        led-matrix-monitoring = pkgs.callPackage ./default.nix {};
      in
      {
        packages = {
          default = led-matrix-monitoring;
          led-matrix-monitoring = led-matrix-monitoring;
        };

        apps = {
          default = {
            type = "app";
            program = "${led-matrix-monitoring}/bin/led-matrix-monitor";
          };
        };

        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            python3
            python3Packages.pyserial
            python3Packages.numpy
            python3Packages.psutil
            python3Packages.evdev
          ];
        };
      }
    ) // {
      # NixOS module for system integration
      nixosModules.led-matrix-monitoring = { config, lib, pkgs, ... }:
        with lib;
        let
          cfg = config.services.led-matrix-monitoring;
          led-matrix-monitoring = pkgs.callPackage ./default.nix {};
        in {
          options.services.led-matrix-monitoring = {
            enable = mkEnableOption "LED Matrix Monitoring service";

            topLeft = mkOption {
              type = types.enum [ "cpu" "net" "disk" "mem-bat" "none" "temp" "fan" ];
              default = "cpu";
              description = "Application to display on top-left quadrant";
            };

            bottomLeft = mkOption {
              type = types.enum [ "cpu" "net" "disk" "mem-bat" "none" "temp" "fan" ];
              default = "mem-bat";
              description = "Application to display on bottom-left quadrant";
            };

            topRight = mkOption {
              type = types.enum [ "cpu" "net" "disk" "mem-bat" "none" "temp" "fan" ];
              default = "disk";
              description = "Application to display on top-right quadrant";
            };

            bottomRight = mkOption {
              type = types.enum [ "cpu" "net" "disk" "mem-bat" "none" "temp" "fan" ];
              default = "net";
              description = "Application to display on bottom-right quadrant";
            };

            disableKeyListener = mkOption {
              type = types.bool;
              default = false;
              description = "Disable keyboard shortcut listener";
            };

            disablePlugins = mkOption {
              type = types.bool;
              default = false;
              description = "Disable plugin system";
            };

            user = mkOption {
              type = types.str;
              default = "root";
              description = "User to run the service as";
            };
          };

          config = mkIf cfg.enable {
            environment.systemPackages = [ led-matrix-monitoring ];

            systemd.services.led-matrix-monitoring = {
              description = "Framework LED Matrix System Monitor";
              wantedBy = [ "multi-user.target" ];
              after = [ "network.target" ];

              serviceConfig = {
                Type = "simple";
                User = cfg.user;
                Group = if cfg.user == "root" then "root" else "users";
                Restart = "always";
                RestartSec = "10s";
              };

              script = let
                args = lib.concatStringsSep " " ([
                  "--top-left ${cfg.topLeft}"
                  "--bottom-left ${cfg.bottomLeft}"
                  "--top-right ${cfg.topRight}"
                  "--bottom-right ${cfg.bottomRight}"
                ] ++ lib.optionals cfg.disableKeyListener [ "--no-key-listener" ]
                  ++ lib.optionals cfg.disablePlugins [ "--disable-plugins" ]);
              in ''
                ${led-matrix-monitoring}/bin/led-matrix-monitor ${args}
              '';
            };

            # Add user to input group if key listener is enabled and not running as root
            users.users = mkIf (!cfg.disableKeyListener && cfg.user != "root") {
              ${cfg.user}.extraGroups = [ "input" ];
            };
          };
        };
    };
}

