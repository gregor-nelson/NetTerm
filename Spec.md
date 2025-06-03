# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

NetTerm is a PyQt6-based network and serial communication tool designed for maritime/offshore environments. It features:
- Serial port communication interface with full configuration support
- Network ping scanner with port scanning capabilities
- Professional marine-inspired UI theme optimized for industrial use
- Scalable UI that adapts to different screen resolutions

## Commands

### Running the Application
```bash
python app.py
```

### Building Executable
```bash
pyinstaller app.spec
```
The built executable will be in the `dist/` directory.

## Architecture

### Core Structure
- **app.py** - Main entry point, initializes PyQt6 application and applies theming
- **core/** - Business logic modules:
  - `ping_scanner.py` - Network scanning with threading and service detection
  - `serial_monitor.py` - Serial communication handling
  - `port_monitor.py` - Port monitoring functionality
  - `serial_thread.py` - Threading for serial operations
  - `command_sequence.py` - Command sequencing utilities
- **ui/** - User interface components:
  - `main_window.py` - Main tabbed window container
  - `serial_tab.py` - Serial communication interface
  - `ping_tab.py` - Network scanning interface
  - `serial_port_scanner.py` - Serial port discovery tab
  - `scaling.py` - UI scaling utilities for responsive design
  - `common_widgets.py` - Shared UI components
- **utils/** - Utility modules:
  - `network_utils.py` - Network helper functions
  - `device_identifier.py` - Device identification utilities

### Key Design Patterns

**Threading Architecture**: Network scanning and serial communication use separate QThread instances to prevent UI blocking. The ping scanner uses concurrent.futures for parallel host scanning.

**UI Scaling**: The UIScaler class (`ui/scaling.py`) calculates scale factors based on screen resolution and provides consistent scaling across all UI elements.

**Theme System**: Centralized theming in `theme_config.py` with a marine-inspired color palette designed for industrial environments. The theme is applied dynamically with scaling support.

**Resource Handling**: The application supports both development and PyInstaller bundled modes with the `resource_path()` helper function for asset loading.

### Serial Communication
The serial monitor supports full configuration (baudrate, parity, stop bits, flow control) with real-time monitoring, hex display modes, and data logging capabilities.

### Network Scanning
The ping scanner performs parallel host discovery with optional port scanning, service detection through signature matching, and exports results to JSON/CSV formats.

## Dependencies
This is a PyQt6 application with dependencies on:
- PyQt6 for the GUI framework
- pyserial for serial communication
- Standard library modules for networking and threading