# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

NetTerm is a PyQt6-based desktop application for network tools, providing:
- Serial port communication and monitoring
- Network ping scanning with port detection
- Serial port discovery and scanning
- Marine-inspired UI theme system

## Architecture

The application follows a modular MVC-like structure:

- `app.py` - Main entry point, initializes PyQt6 app and applies themes
- `ui/` - UI components and widgets
  - `main_window.py` - Main application window with tab management
  - `serial_tab.py` - Serial communication interface
  - `ping_tab.py` - Network ping scanning interface
  - `serial_port_scanner.py` - Serial port discovery interface
  - `scaling.py` - UI scaling utilities for different screen resolutions
  - `common_widgets.py` - Shared UI components
- `core/` - Business logic and core functionality
  - `ping_scanner.py` - Network scanning with threading support
  - `serial_monitor.py` - Serial port communication logic
  - `serial_thread.py` - Threading for serial operations
  - `port_monitor.py` - Port monitoring functionality
  - `command_sequence.py` - Command sequence management
- `utils/` - Utility modules
  - `network_utils.py` - Network utilities (ping, hostname resolution, port scanning)
  - `device_identifier.py` - Device identification helpers
- `theme_config.py` - Comprehensive theme system with marine-inspired styling

## Key Design Patterns

### Threading Architecture
- Uses QThread for non-blocking network operations
- `PingWorker` class handles individual ping operations with multiple detection methods
- Serial operations run in separate threads to prevent UI freezing

### UI Scaling System
- `UIScaler` class provides responsive scaling based on screen resolution and DPI
- All dimensions and fonts scale proportionally
- Supports both small and high-DPI displays

### Theme System
- Marine-inspired professional theme with industrial elements
- Color palette defined in `COLORS` dictionary in `theme_config.py`
- Scaled stylesheets generated dynamically based on UI scale factor
- Support for dark, light, and night vision themes

### Tab-based Architecture
- Main window uses QTabWidget for different tool modes
- Each tab is self-contained with its own signal/slot connections
- Status messages propagate from tabs to main window status bar

## Development Commands

### Running the Application
```bash
python app.py
```

### Building Executable
The project includes PyInstaller configuration:
```bash
pyinstaller app.spec
```

## Important Implementation Details

### Network Scanning
- Multi-method host detection (ICMP ping + TCP ping for ICMP-blocked hosts)
- Concurrent port scanning with ThreadPoolExecutor
- Service identification for common ports
- IP range support including CIDR notation

### Serial Communication
- Automatic serial port discovery and monitoring
- Thread-safe serial operations
- Real-time data display with TX/RX separation

### UI Responsiveness
- All blocking operations (network scans, serial I/O) run in background threads
- Progress updates via Qt signals
- Proper cleanup on application close

### Resource Management
- Icon bundling for PyInstaller builds
- Proper thread cleanup on application exit
- Memory-efficient handling of large IP ranges