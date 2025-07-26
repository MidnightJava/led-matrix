{ lib
, python3
, fetchFromGitHub
, makeWrapper
}:

python3.pkgs.buildPythonApplication rec {
  pname = "led-matrix-monitoring";
  version = "1.0.0";
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
  ];

  installPhase = ''
    mkdir -p $out/bin
    mkdir -p $out/lib/python${python3.pythonVersion}/site-packages/led_matrix_monitoring
    
    # Copy Python files
    cp *.py $out/lib/python${python3.pythonVersion}/site-packages/led_matrix_monitoring/
    
    # Copy plugins directory
    cp -r plugins $out/lib/python${python3.pythonVersion}/site-packages/led_matrix_monitoring/
    
    # Create wrapper script with proper Python environment
    makeWrapper ${python3.withPackages (ps: with ps; [ pyserial numpy psutil evdev ])}/bin/python $out/bin/led-matrix-monitor \
      --add-flags "$out/lib/python${python3.pythonVersion}/site-packages/led_matrix_monitoring/led_system_monitor.py" \
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

