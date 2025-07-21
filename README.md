# NetTerm

Network diagnostic and serial communication tool built with PyQt6.

## Features

**Network Scanning**
- ICMP and TCP host discovery
- Port scanning with service detection
- Network adapter enumeration
- Results export (JSON, CSV, XML)

**Serial Communication** 
- Real-time port monitoring
- Command sequences with timing
- Hex/ASCII display modes
- Data throughput tracking

**Interface**
- Responsive UI scaling
- Tab-based layout
- Dark theme

## Implementation

### Structure
```
NetTerm/
├── core/           # Threading and business logic
├── ui/             # Interface components
├── utils/          # Network utilities
└── theme_config.py # Styling
```

### Network Scanning
- Multi-threaded host discovery using `concurrent.futures`
- Falls back to TCP connect when ICMP is blocked
- Service identification through banner grabbing
- Qt signals for thread-safe UI updates

### Serial Communication
- Separate thread for non-blocking serial I/O
- Configurable baud rates, parity, stop bits
- Command history and auto-completion
- Real-time RX/TX statistics

### UI Implementation
- Dynamic scaling based on screen DPI
- Custom Qt stylesheets with marine colour palette
- Mutex-protected data structures for thread safety

## Installation

```bash
pip install -r requirements.txt
python app.py
```

**Dependencies**
- PyQt6 ≥6.0.0
- pyserial ≥3.4

**Building executable**
```bash
pyinstaller app.spec
```

## Technical Notes

- Uses Qt's signal/slot mechanism for thread communication
- Worker threads handle blocking operations (network scans, serial I/O)
- Handles large IP ranges through batched processing
- Custom UI scaling system for different screen sizes
- Resource cleanup on application exit
