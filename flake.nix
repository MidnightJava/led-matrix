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
            python3Packages.pynput
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

          yamlFormat = pkgs.formats.yaml {};

          # Helper to convert old-style config to YAML
          # Note: 'app' key must be present (set to null) for the Python code to work
          legacyToYaml = {
            duration = 10;
            quadrants = {
              top-left = [{
                app = null;  # Required by led_system_monitor.py
                name = cfg.topLeft;
                duration = 10;
                animate = false;
              }];
              top-right = [{
                app = null;
                name = cfg.topRight;
                duration = 10;
                animate = false;
              }];
              bottom-left = [{
                app = null;
                name = cfg.bottomLeft;
                duration = 10;
                animate = false;
              }];
              bottom-right = [{
                app = null;
                name = cfg.bottomRight;
                duration = 10;
                animate = false;
              }];
            };
          };

          # Determine which config to use
          configFile =
            if cfg.configFile != null then cfg.configFile
            else if cfg.config != null then yamlFormat.generate "led-matrix-config.yaml" cfg.config
            else if cfg.topLeft != null then yamlFormat.generate "led-matrix-config.yaml" legacyToYaml
            else throw "services.led-matrix-monitoring: either config, configFile, or legacy options must be set";
        in {
          options.services.led-matrix-monitoring = {
            enable = mkEnableOption "LED Matrix Monitoring service";

            config = mkOption {
              type = types.nullOr yamlFormat.type;
              default = null;
              description = ''
                Configuration for LED Matrix monitoring as a Nix attrset.
                This will be converted to YAML. Mutually exclusive with configFile.

                See example config.yaml in the package for the full schema.
              '';
              example = literalExpression ''
                {
                  duration = 10;
                  quadrants = {
                    top-left = [{
                      app = {
                        name = "cpu";
                        duration = 10;
                        animate = false;
                      };
                    }];
                    bottom-left = [{
                      app = {
                        name = "mem-bat";
                        duration = 10;
                        animate = false;
                      };
                    }];
                    top-right = [{
                      app = {
                        name = "disk";
                        duration = 10;
                        animate = false;
                      };
                    }];
                    bottom-right = [{
                      app = {
                        name = "net";
                        duration = 10;
                        animate = false;
                      };
                    }];
                  };
                }
              '';
            };

            configFile = mkOption {
              type = types.nullOr types.path;
              default = null;
              description = ''
                Path to YAML configuration file.
                Mutually exclusive with config.
              '';
            };

            # Legacy options for backward compatibility
            topLeft = mkOption {
              type = types.nullOr (types.enum [ "cpu" "net" "disk" "mem-bat" "none" "temp" "fan" ]);
              default = null;
              description = ''(DEPRECATED) Application to display on top-left quadrant. Use config or configFile instead.'';
            };

            bottomLeft = mkOption {
              type = types.nullOr (types.enum [ "cpu" "net" "disk" "mem-bat" "none" "temp" "fan" ]);
              default = null;
              description = ''(DEPRECATED) Application to display on bottom-left quadrant. Use config or configFile instead.'';
            };

            topRight = mkOption {
              type = types.nullOr (types.enum [ "cpu" "net" "disk" "mem-bat" "none" "temp" "fan" ]);
              default = null;
              description = ''(DEPRECATED) Application to display on top-right quadrant. Use config or configFile instead.'';
            };

            bottomRight = mkOption {
              type = types.nullOr (types.enum [ "cpu" "net" "disk" "mem-bat" "none" "temp" "fan" ]);
              default = null;
              description = ''(DEPRECATED) Application to display on bottom-right quadrant. Use config or configFile instead.'';
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
            # Validation
            assertions = [
              {
                assertion = (cfg.config == null) || (cfg.configFile == null);
                message = "services.led-matrix-monitoring: config and configFile are mutually exclusive";
              }
              {
                assertion = (cfg.config != null) || (cfg.configFile != null) || (cfg.topLeft != null);
                message = "services.led-matrix-monitoring: either config, configFile, or legacy options must be set";
              }
            ];

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

              environment = {
                # Point to the generated or provided config file
                CONFIG_FILE = configFile;
              };

              script = let
                args = lib.concatStringsSep " " (
                  lib.optionals cfg.disableKeyListener [ "--no-key-listener" ]
                  ++ lib.optionals cfg.disablePlugins [ "--disable-plugins" ]
                );
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

