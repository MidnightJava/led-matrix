{ lib
, python3
, fetchFromGitHub
, makeWrapper
}:

python3.pkgs.buildPythonApplication rec {
  pname = "led-matrix-monitoring";
  version = "1.2.0-yaml";
  format = "other";

  src = ./.;

  nativeBuildInputs = [
    makeWrapper
    python3.pkgs.setuptools
    python3.pkgs.wheel
  ];

  propagatedBuildInputs = with python3.pkgs; [
    pyserial
    numpy
    psutil
    evdev
    pynput
    pyyaml  # Required for YAML config parsing
    python-dotenv  # Required for environment variable loading
    requests  # Required for time_weather_plugin
    # Note: iplocate is not available in nixpkgs - time_weather_plugin will need to handle this gracefully
  ];

  installPhase = ''
    mkdir -p $out/bin
    mkdir -p $out/lib/python${python3.pythonVersion}/site-packages
    mkdir -p $out/share/led-matrix
    
    # Copy the entire led_mon module
    cp -r led_mon $out/lib/python${python3.pythonVersion}/site-packages/
    
    # Exclude time_weather_plugin due to unavailable iplocate dependency in nixpkgs
    rm -f $out/lib/python${python3.pythonVersion}/site-packages/led_mon/plugins/time_weather_plugin.py
    
    # Copy main.py to the package root
    cp main.py $out/lib/python${python3.pythonVersion}/site-packages/
    
    # Copy example config and .env to share for reference
    cp led_mon/config.yaml $out/share/led-matrix/config.example.yaml
    cp led_mon/.env-example $out/share/led-matrix/.env-example
    
    # Create wrapper script with proper Python environment
    makeWrapper ${python3.withPackages (ps: with ps; [ pyserial numpy psutil evdev pynput pyyaml python-dotenv requests ])}/bin/python $out/bin/led-matrix-monitor \
      --add-flags "$out/lib/python${python3.pythonVersion}/site-packages/main.py" \
      --prefix PYTHONPATH : "$out/lib/python${python3.pythonVersion}/site-packages"
  '';

  # Skip tests for now since there aren't any
  doCheck = false;

  meta = with lib; {
    description = "System monitoring application for Framework 16 LED Matrix Panels";
    longDescription = ''
      This software displays system performance characteristics in real-time
      on Framework 16 laptop LED Matrix Panels, including CPU utilization,
      battery status, memory usage, disk I/O, network traffic, temperatures,
      and fan speeds. Includes robustness improvements for permission handling
      and graceful degradation when hardware is not available.
    '';
    homepage = "https://code.karsttech.com/jeremy/FW_LED_System_Monitor.git";
    license = licenses.mit; # Assuming MIT, adjust if different
    maintainers = [ ];
    platforms = platforms.linux;
    mainProgram = "led-matrix-monitor";
  };
}

