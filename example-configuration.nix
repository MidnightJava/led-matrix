# Example NixOS configuration for Framework 16 LED Matrix Monitoring
# Add this to your configuration.nix or import it as a module

{ config, lib, pkgs, ... }:

{
  # For flake users, add this to your flake.nix inputs:
  # led-matrix-monitoring = {
  #   url = "github:timoteuszelle/led-matrix/fix/robustness-and-permission-handling";
  #   inputs.nixpkgs.follows = "nixpkgs";
  # };
  # And add led-matrix-monitoring.nixosModules.led-matrix-monitoring to your modules list

  # Enable the LED Matrix Monitoring service
  services.led-matrix-monitoring = {
    enable = true;
    
    # Standard configuration
    topLeft = "cpu";          # CPU usage in top-left
    bottomLeft = "mem-bat";   # Memory + battery in bottom-left
    topRight = "disk";        # Disk I/O in top-right
    bottomRight = "net";      # Network traffic in bottom-right
    
    # Optional: Add temperature and fan monitoring
    # topRight = "temp";
    # bottomRight = "fan";
    
    # Optional: Disable keyboard shortcut (Alt+I)
    # disableKeyListener = true;
    
    # Optional: Disable plugins
    # disablePlugins = true;
    
    # Optional: Run as specific user instead of root
    # user = "your-username";
  };

  # Optional: Add the package to system packages for manual use
  # environment.systemPackages = [
  #   led-matrix-monitoring.packages.${pkgs.system}.default
  # ];
}

