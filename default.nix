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
    mkdir -p $out/lib/python${python3.pythonVersion}/site-packages/led_matrix_monitoring
    mkdir -p $out/share/led-matrix
    
    # Copy Python files
    cp *.py $out/lib/python${python3.pythonVersion}/site-packages/led_matrix_monitoring/
    
    # Copy data directories to the SAME location as Python files
    # The code expects plugins, snapshot_files, and config.yaml in the same directory as the .py files
    # Exclude time_weather_plugin due to unavailable iplocate dependency in nixpkgs (need to add a way to build the dep from source?)
    mkdir -p $out/lib/python${python3.pythonVersion}/site-packages/led_matrix_monitoring/plugins
    cp plugins/__init__.py $out/lib/python${python3.pythonVersion}/site-packages/led_matrix_monitoring/plugins/
    cp plugins/temp_fan_plugin.py $out/lib/python${python3.pythonVersion}/site-packages/led_matrix_monitoring/plugins/
    # Skip time_weather_plugin.py - requires iplocate which is not available in nixpkgs
    cp -r snapshot_files $out/lib/python${python3.pythonVersion}/site-packages/led_matrix_monitoring/
    cp config.yaml $out/lib/python${python3.pythonVersion}/site-packages/led_matrix_monitoring/
    
    # Also copy example config to share for reference
    cp config.yaml $out/share/led-matrix/config.example.yaml
    
    # Create wrapper script with proper Python environment and config support
    makeWrapper ${python3.withPackages (ps: with ps; [ pyserial numpy psutil evdev pynput pyyaml python-dotenv requests ])}/bin/python $out/bin/led-matrix-monitor \
      --add-flags "$out/lib/python${python3.pythonVersion}/site-packages/led_matrix_monitoring/main.py" \
      --prefix PYTHONPATH : "$out/lib/python${python3.pythonVersion}/site-packages/led_matrix_monitoring"
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

