<div align="center">

# ⚡ NEXUS AI (v2.0 Enterprise Release)
### Autonomous Multimodal Desktop Operating Core & 3D Holographic OS

[![Release v2.0.0](https://img.shields.io/badge/Release-v2.0.0-0A84FF?style=for-the-badge&logo=github)](https://github.com/Duckierpine3108/Nexus-AI/releases/latest)
[![Platform Windows](https://img.shields.io/badge/Platform-Windows_10%20%7C%2011_x64-0078D6?style=for-the-badge&logo=windows&logoColor=white)](https://www.microsoft.com/windows)
[![Python 3.11](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![PyQt6](https://img.shields.io/badge/PyQt6-Frosted_Glass_HUD-41CD52?style=for-the-badge&logo=qt&logoColor=white)](https://riverbankcomputing.com/software/pyqt/)
[![Gemini Live 2.5](https://img.shields.io/badge/Gemini_Live-2.5_Flash_Audio-8E75B2?style=for-the-badge&logo=googlebard&logoColor=white)](https://deepmind.google/technologies/gemini/)
[![License](https://img.shields.io/badge/License-MIT-F5A623?style=for-the-badge)](LICENSE)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Kamran_Jalil-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/kamranjalilkhan/)

<br />

> **NEXUS AI** is an enterprise-grade, autonomous desktop operating system companion engineered specifically for Windows workstations. Conceived and orchestrated by an **AI Agent Architect through pure Vibe-Coding**, it bridges low-latency natural voice interaction with native OS-level control. Powered by Google's native bi-directional **Gemini 2.5 Flash Live Audio API**, offline **Vosk Kaldi** neural wake engines, and a hardware-accelerated **3D Three.js holographic avatar**, it acts as a permanent digital co-pilot. It answers WhatsApp desktop calls, automates multi-engine browsers, manages Steam/Epic Games libraries, controls Sony Bravia smart displays over Wi-Fi, monitors GPU telemetry via direct NVML ctypes, and self-heals its own codebase in real time.

<br />

---

### 📥 One-Click Windows Installer Available
**You do not need to install Python, configure virtual environments, or compile source code.**  
Download the prebuilt, standalone installer **`nexus_ai_setup_v2.0.exe`** directly from the **[GitHub Releases Tab](https://github.com/Duckierpine3108/Nexus-AI/releases/latest)**.

---

</div>

## 📸 Interface Preview

<div align="center">
  <img src="assets/nexus_ui_preview.png" alt="NEXUS AI Interface" width="850" style="border-radius: 10px; box-shadow: 0px 4px 25px rgba(0, 255, 255, 0.25);" />
  <p><i>Real-time 3D reactive avatar mesh (head.glb) rendered in Three.js WebGL with phoneme viseme lip-sync, quantum arc core, and 5-mode adaptive frosted-glass HUD.</i></p>
</div>

---

## 💡 Why NEXUS AI?

Standard conversational AI interfaces live isolated inside browser tabs or text-based chat windows. They possess zero awareness of your operating system, suffer from high-latency request-response cycles, and cannot interact with local software, hardware, or files.

**NEXUS AI shatters this barrier.** It runs as a high-performance desktop command core that:
1. **Listens Privately & Reacts Instantly:** Gated behind a 100% offline local wake-word engine (*"Hey Nexus"*, *"Computer"*), streaming duplex audio with instant interruption (barge-in) capability.
2. **Governs the Entire OS:** Directly drives Win32 system APIs, monitors GPU core loads and VRAM without spawning subprocesses, snaps windows pixel-perfectly, and organizes file-systems.
3. **Controls Real-World Devices:** Manages WhatsApp calls, controls smart TVs over local Wi-Fi REST endpoints, and tracks fleet hardware distances with spherical Haversine radar.
4. **Self-Heals Its Own Code:** Analyzes runtime traceback errors, queries Gemini reasoning models, and dynamically hot-reloads patched Python modules into memory with zero application downtime.

---

## 🏛️ System Architecture

```text
 ┌───────────────────────────────────────────────────────────┐
 │                   HARDWARE AUDIO INPUT                    │
 └─────────────────────────────┬─────────────────────────────┘
                               │
                  (Local Offline Neural Gate)
                               ▼
 ┌───────────────────────────────────────────────────────────┐
 │           Vosk Kaldi Engine (Offline Wake Word)           │
 │               "Hey Nexus"  /  "Computer"                  │
 └─────────────────────────────┬─────────────────────────────┘
                               │ (Keyword Detected -> Mic Unmuted)
                               ▼
 ┌───────────────────────────────────────────────────────────┐
 │      Google Gemini 2.5 Flash Native Audio WebSocket       │
 │        Full-Duplex Bidirectional 16kHz/24kHz PCM          │
 └─────────────────────────────┬─────────────────────────────┘
                               │
                 (Real-time Function Calling)
                               ▼
 ┌───────────────────────────────────────────────────────────┐
 │            NEXUS CORE TOOL ROUTER (main.py)               │
 ├───────────────────────────────────────────────────────────┤
 │  • Dynamic Zero-Restart Hot Reloading (importlib.reload)  │
 │  • AST Structural Wipe Shield (>35% Reduction Blocker)    │
 │  • Dual-Channel Delivery: 2-Sentence Voice + HUD Stream   │
 └──────┬──────────────────────┬───────────────────────┬─────┘
        │                      │                       │
        ▼                      ▼                       ▼
 ┌───────────────┐      ┌───────────────┐      ┌───────────────┐
 │ OS & Hardware │      │ Browser & Web │      │ Communication │
 │ - NVML Ctypes │      │ - Playwright  │      │ - WhatsApp UI │
 │ - Win32 APIs  │      │ - 5 Browsers  │      │ - OS DeepLink │
 │ - Process Kill│      │ - Live Ground │      │ - Telephony   │
 └──────┬────────┘      └───────┬───────┘      └───────┬───────┘
        │                       │                      │
        └───────────────────────┼──────────────────────┘
                                ▼
 ┌───────────────────────────────────────────────────────────┐
 │      PyQt6 Frosted-Glass HUD & Dedicated Audio Engine     │
 │  • Three.js WebGL Viewport (head.glb) & Viseme Lip-Sync   │
 │  • Quantum Arc Core (Listening / Thinking / Standby)      │
 │  • 5-Mode Adaptive HUD (Chat, Reasoning, Radar, Stats)   │
 │  • 3.5x Soft Tanh DSP Audio Saturation Pre-Amp Booster    │
 └───────────────────────────────────────────────────────────┘
🚀 Architectural Superpowers & Core Subsystems
1. 🎙️ Dual-Engine Audio Pipeline (Offline Vosk + Gemini Live)
Privacy-First Offline Gate: Vosk Kaldi offline speech engine continuously analyzes local microphone buffers for the wake phrases "Hey Nexus" or "Computer". Zero ambient room audio is transmitted to the cloud until triggered.
Full-Duplex Duplex Speech: Bidirectional 16kHz PCM input and 24kHz PCM output over low-latency WebSockets via gemini-2.5-flash-native-audio-preview. Supports instant conversational interruptions (barge-in).
DSP Pre-Amp Booster: Integrated digital signal processor runs a 3.5x gain multiplier through a soft hyperbolic tangent (tanh) saturation curve, boosting speech volume without digital clipping or distortion.
2. 🧊 3D Holographic Avatar & Multi-Mode Adaptive HUD
Phoneme-Driven Viseme Lip-Sync: Translates incoming audio energy frequencies and visemes into real-time 3D morph target weights on a custom head mesh (head.glb) served via Three.js in a PyQt6 Chromium WebEngine viewport.
Quantum Arc Core: Visualizes AI thinking, listening, and idle standby states through a dynamic, audio-reactive energy sphere.
5-Mode Adaptive HUD:
Mode 1 (Conversational HUD): Clean dialogue cards with user transcripts and agent summaries.
Mode 2 (Reasoning & Code HUD): Dual-pass adversarial red-teaming and code diff visualizer.
Mode 3 (Hardware Telemetry): Real-time GPU/CPU gauges, VRAM graphs, and process lists.
Mode 4 (Compact Float Companion): Detaches the 3D avatar into an unobtrusive floating desk widget.
Mode 5 (Full Satellite Radar): Deep-zoom Leaflet 3D satellite map for device tracking.
3. 🔄 Live Zero-Restart Hot-Reloading & AST Self-Evolution
Dynamic RAM Reloading: The central router in main.py monitors disk timestamps (mtime) on all actions/*.py. Saving any action file (Ctrl + S) instantly reloads the module via importlib.reload() without interrupting active voice sessions or restarting the process.
AST Structural Wipe Shield: actions/self_evolution.py parses Abstract Syntax Trees (AST) of incoming code patches. Any patch that drops more than 35% of a module's classes or functions is rejected, preventing LLM hallucinations from wiping files.
Surgical Diff Patching: Implements whitespace- and quote-tolerant search-and-replace to patch specific functions autonomously.
4. 📞 WhatsApp Desktop Telephony & Automation Suite
NEXUS directly interfaces with and automates the native Windows WhatsApp Desktop client:
Voice & Video Calling: Initiates voice and video calls (whatsapp_call), answers incoming calls (whatsapp_accept_call), and hangs up cleanly on voice command.
Smart Call Decline with Auto-SMS: Declines incoming calls and automatically dispatches a polite, contextual explanation to the caller via chat (whatsapp_decline_call).
Incoming Ring Radar: A background listener continuously detects desktop ring events, raises system volume, and alerts the operator.
File & Screenshot Delivery: Captures active desktop displays or selects local target files and delivers them directly into contact chat threads (whatsapp_send_screenshot, whatsapp_send_file).
5. 🎮 Steam & Epic Games Automated Fleet Manager
Background Game Updates: Verifies update statuses and triggers downloads for Steam and Epic Games libraries (game_updater.py).
Protocol Launching: Launches games instantly via protocol URIs (steam://run/<id>).
Off-Peak Nightly Scheduling: Schedules heavy installations or patches during late-night hours.
Auto-Shutdown Watchdog: Automatically powers down the computer when all downloads and patches reach 100% completion.
6. 📺 Sony Bravia Smart IP Display & TV Controller
Direct Hardware REST API: Controls Sony Bravia Smart TVs directly over local Wi-Fi using pre-shared key (PSK) authentication.
Display Teleportation: Teleports active browser windows seamlessly between the primary workstation monitor (Display 1) and the Sony TV (Display 2).
HDMI Input Switching & Controls: Switches between HDMI 1–4, adjusts hardware volume, toggles mute, and sends power commands over IP.
DPI-Aware Ad Skipping: Automatically detects and skips YouTube TV ads using scale-independent coordinate mapping.
7. 👁️ Biomimetic Gaze Tracking & Ergonomic Sentinel
3D Euler Head Pose Estimation: Calculates real-time Yaw, Pitch, and Roll using OpenCV solvePnP and facial landmark geometries (actions/gaze_tracker.py).
Fatigue & Drowsiness Radar: Continuously computes Eye Aspect Ratios (EAR) to detect micro-sleeps, excessive blinking, or eye strain.
Cognitive Screen Engagement Score: Evaluates visual focus (0–100%) and proactively warns the operator when prolonged fatigue is detected.
8. 🏋️ Biomechanical Pushup & Athletic Coach
3D Joint Angle Kinematics: Tracks shoulder, elbow, and hip joint vectors using MediaPipe 3D pose estimation (actions/pushup_counter.py).
Strict ROM Verification: Enforces a full 90-degree elbow flexion and flat spine alignment—rejects half-reps and poor form.
Auditory Cadence Coaching: Speaks rep counts and cadence cues out loud ("Down... Up... 10 reps, keep your back straight!").
Persistent PR Tracking: Calculates real MET calisthenics calorie burns and persists lifetime personal records inside memory/long_term.json.
⚡ The 29 Autonomous Agent Tools
Every tool in the actions/ library is isolated, thread-safe, and built with low-level OS protocols:
#	Action Tool	Module	Core Functionality	Underlying Technology
01	Browser Controller	browser_control.py	Multi-engine Chromium, Firefox, WebKit automation. Handles cookie modals and dangling profile lockfiles.	Playwright, Chrome DevTools
02	Self-Evolution Core	self_evolution.py	Autonomous self-healing code modifier with AST structural wipe shields and surgical patching.	Python AST, Gemini Flash-Lite
03	Deep Think Reflection	deep_think.py	Multi-stage agentic reflection (Stage 1: Adversarial Red-Teaming; Stage 2: Enterprise Blueprint).	Dual-Pass Reflection, HUD Sync
04	Web Search Engine	web_search.py	Hybrid search engine with gzip RSS feed decompression and parallel multi-item comparison matrix.	Gzip, ThreadPoolExecutor
05	Cross-Platform Comms	send_message.py	Messaging transceiver via direct OS URI protocols (tg://, discord://, whatsapp://).	Win32 Ctypes, OS Deep-Links
06	YouTube Media Core	youtube_video.py	Media playback controller, transcript analyzer, and PK regional redirect bypass with Win32 controls.	Transcripts API, Win32 Media
07	Desktop Governance	desktop.py	Pixel-perfect window snapping (SPI_GETWORKAREA), wallpaper caching, and silent recycle bin purge.	Win32 Ctypes, Shell32
08	Hardware Monitor	system_monitor.py	Hardware governor reporting NVML GPU core loads, VRAM, temps, and remedial rogue process termination.	NVML Ctypes, PSUtil
09	Proactive Intelligence	proactive.py	Ambient intelligence core with fullscreen gaming guard, video call shield, and circadian quiet hours.	GetLastInputInfo, DND Guard
10	Background Sentinel	background_monitor.py	Unified proactive query agent reporting active background tasks and quiet-hour governance.	Proactive Dispatch Engine
11	Sony TV Controller	tv_controller.py	Sony Bravia Smart IP Wi-Fi controller (REST API, input HDMI switching, DPI-safe ad skipping).	Sony Bravia REST API, Wi-Fi
12	Flight Route Matrix	flight_finder.py	Sub-2s live flight grounding matrix across global and domestic IATA codes with multi-currency math.	Live Grounding, IATA DB
13	Video Publisher	upload_video.py	Video publisher injecting file paths directly into OS open-file dialogs for TikTok & YouTube Studio.	Win32 OpenDialog, Gemini SEO
14	Spatial Fleet Radar	device_tracker.py	Fleet locator calculating spherical Haversine distances with local reverse geocoding and 3D radar.	Leaflet 3D Radar, Geolocation
15	Biomimetic Gaze	gaze_tracker.py	3D Euler head-pose estimator (OpenCV solvePnP), Eye Aspect Ratio (EAR) blink/fatigue scoring.	OpenCV, MediaPipe Face Mesh
16	Game Fleet Updater	game_updater.py	Steam & Epic Games launcher via protocol URIs (steam://run) and ACF manifest verification.	Protocol Handlers, VDF/ACF
17	Pushup Coach	pushup_counter.py	3D biomechanical joint alignment coach with real-time audio cadence and persistent PR tracking.	MediaPipe 3D, MET Formula
18	WhatsApp Telephony	whatsapp_controller.py	Automated communication daemon with voice/video call automation and screenshot delivery.	Win32 UI Automation, Hooks
19	Weather Telemetry	weather_report.py	Real-time meteorological intelligence and multi-day forecasting across global coordinates.	Meteorological Telemetry APIs
20	Screen Vision & OCR	screen_processor.py	Real-time desktop frame capture, OCR extraction, and visual context grounding.	Win32 GDI, OCR Engine
21	Universal File Suite	file_processor.py	22-action file processor: PDF-to-Word, text extraction, audio stripping, video trimming, CSV math.	LXML, PyPDF, PPTX, MoviePy
22	File System Governor	file_controller.py	File-system governance, directory reorganization, and automated file dispatch.	Windows Shell APIs
23	Computer Driver	computer_control.py	Low-level OS input driver (mouse clicks, smooth scrolls, keyboard shortcuts).	Direct Win32 Ctypes
24	System Settings Core	computer_settings.py	Master OS control (system audio, display brightness, Wi-Fi state, Bluetooth toggles).	Windows Management (WMI)
25	App Shell Launcher	open_app.py	Instant executable and shell protocol launcher.	Windows ShellExecuteW
26	Circadian Reminder	reminder.py	Circadian scheduling and audible voice notifications engine.	Persistent Task Storage
27	Code Helper & Linter	code_helper.py	Live syntax checking, code formatting, and AST snippet generation.	Python AST, Code Formatters
28	Dev Agent Scaffolder	dev_agent.py	Autonomous multi-file project scaffolding, terminal runner, and automated pip installer.	Subprocess Concurrency
29	Codebase Inspector	codebase_inspector.py	Full directory tree code mapping, security audit, and dependency validator.	Static Code Analysis
🔒 Encrypted Web Dashboard & Mobile Relay
Local TLS/SSL Command Server: Embedded FastAPI/Uvicorn server secured with self-signed TLS/SSL certificates (config/certs/jarvis.crt).
Mobile Telephony Relay: Scan the on-screen QR code from any smartphone (Android/iOS) on your local Wi-Fi to establish a secure WebSocket audio link. Stream mobile microphone audio directly into Nexus AI from across the room.
📁 Repository Structure
code
Text
Nexus-AI/
├── actions/                  # 29 Modular OS-Level Agent Tool Engines
│   ├── background_monitor.py # Ambient monitor query agent
│   ├── browser_control.py    # Playwright multi-engine browser controller
│   ├── codebase_inspector.py # Project tree mapper & security auditor
│   ├── code_helper.py        # Code formatting and AST snippet engine
│   ├── computer_control.py   # Low-level Win32 keyboard/mouse driver
│   ├── computer_settings.py  # OS brightness, audio, and network toggles
│   ├── deep_think.py         # Dual-pass agentic reasoning reflection
│   ├── desktop.py            # Workspace governance & pixel-perfect snapping
│   ├── device_tracker.py     # Haversine spatial fleet & GPS radar
│   ├── dev_agent.py          # Autonomous multi-file project builder
│   ├── file_controller.py    # File-system governance & desktop organizer
│   ├── file_processor.py     # Universal 22-action document & media suite
│   ├── flight_finder.py      # Sub-2s live flight grounding & route matrix
│   ├── game_updater.py       # Steam & Epic Games fleet patcher
│   ├── gaze_tracker.py       # 3D Euler head-pose & cognitive fatigue radar
│   ├── open_app.py           # Win32 ShellExecute app launcher
│   ├── proactive.py          # Circadian DND, gaming & call guard
│   ├── pushup_counter.py     # 3D biomechanical joint coach & PR tracker
│   ├── reminder.py           # Circadian voice alert & task scheduler
│   ├── screen_processor.py   # High-speed desktop frame capture & OCR
│   ├── self_evolution.py     # AST self-healing & surgical code patcher
│   ├── send_message.py       # Cross-platform URI deep-link transceiver
│   ├── system_monitor.py     # Zero-subprocess NVML GPU & hardware governor
│   ├── tv_controller.py      # Sony Bravia Smart IP Wi-Fi controller
│   ├── upload_video.py       # TikTok & YouTube automated studio publisher
│   ├── weather_report.py     # Meteorological forecasting engine
│   ├── web_search.py         # Sub-200ms Instant Answer & comparison search
│   ├── whatsapp_controller.py# Full WhatsApp desktop telephony automation
│   └── youtube_video.py      # YouTube PK feed bypass & transcript analyzer
├── assets/                   # UI previews, branding logos, icons
├── config/                   # Workstation configuration, certs, and telemetry
│   ├── certs/                # Local SSL certificates (jarvis.crt, jarvis.key)
│   ├── devices_telemetry.json# Hardware telemetry state
│   └── nexus.ico             # Application execution icon
├── core/                     # Internal STT, TTS, LLM clients, and system prompts
│   └── prompt.txt            # Master cognitive operating system prompt
├── dashboard/                # Encrypted FastAPI/Uvicorn server & web interfaces
│   ├── static/               # HTML/JS mobile pairing client
│   ├── server.py             # Encrypted WebSocket & HTTP gateway
│   └── watch.html            # Real-time remote telemetry dashboard
├── memory/                   # Persistent long-term memory & PR storage
│   ├── config_manager.py     # Dynamic configuration persistence
│   ├── long_term.json        # Permanent user records and pushup PRs
│   └── memory_manager.py     # Contextual vector & session manager
├── model/                    # Offline Vosk Kaldi speech acoustic model weights
├── plugins/                  # Dynamic third-party plugin extension directory
├── head.glb                  # Custom 3D holographic avatar mesh
├── index.html                # Three.js WebGL viewport rendering layer
├── main.py                   # Central orchestration engine & live WebSocket loop
├── ui.py                     # PyQt6 frosted-glass UI & 5-mode adaptive HUD
├── nexus_ai.spec             # Production PyInstaller compilation blueprint
├── nexus_ai.iss              # Enterprise Inno Setup Windows installer script
├── requirements.txt          # Python dependency specifications
└── README.md                 # Master system documentation
📦 Installation & Setup
Method A: One-Click Windows Installer (Recommended)
Download nexus_ai_setup_v2.0.exe from the NEXUS AI Releases Page.
Run the installer and follow the setup wizard (Administrator privileges are recommended for Win32 OS-level window snapping and hardware monitoring).
Launch NEXUS AI from your Desktop or Start Menu shortcut.
Enter your Google Gemini API Key on the initialization screen to begin.
Method B: Run From Source (Developers)
Prerequisites
Windows 10 or 11 (64-bit)
Python 3.11 installed
Microsoft Visual C++ 2015–2022 Redistributable (x64)
Google Gemini API Key
Step-by-Step Setup
code
Bash
# 1. Clone the repository
git clone https://github.com/Duckierpine3108/Nexus-AI.git
cd Nexus-AI

# 2. Create and activate a Python 3.11 virtual environment
python -m venv venv
venv\Scripts\activate

# 3. Install core dependencies
pip install -r requirements.txt

# 4. Install Playwright browser binaries
playwright install chromium

# 5. Configure environment variables (.env)
# Create a .env file in the root directory:
GEMINI_API_KEY=your_google_gemini_api_key_here

# 6. Launch the Nexus AI Core
python main.py
⚙️ Compiling the Standalone Installer
To build the standalone executable and Inno Setup installer from source:
code
Cmd
:: 1. Compile the standalone binary distribution
pyinstaller nexus_ai.spec --noconfirm

:: 2. Compile the Windows Installer using Inno Setup 6
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" nexus_ai.iss
The compiled installer will be generated at Output\nexus_ai_setup_v2.0.exe.
🔒 Security, Privacy & Safety Guards
Offline Audio Gating: Zero microphone audio leaves your local machine until the offline Vosk neural wake engine detects the wake phrase.
AST Code-Wipe Shield: The autonomous self-evolution engine parses code syntax trees and blocks any update that drops more than 35% of an action file's structure.
OS Process Critical Shield: The hardware governor strictly forbids terminating critical Windows system processes (svchost.exe, csrss.exe, lsass.exe, explorer.exe).
Circadian Quiet Hours Guard: Proactive voice interactions are automatically silenced between 11:30 PM and 7:00 AM PKT to prevent unwanted disturbances.
Sensory Media Shield: Voice interruptions are automatically suppressed when full-screen gaming, video calls (Zoom, Teams, Meet), or media playback are active.
🤝 Acknowledgments & Credits
Foundational Inspiration: Early structural concepts for the desktop interface viewport were inspired by the open-source explorations of Faith Make.
NEXUS AI Evolution: Elevated into a full enterprise desktop operating core through pure Vibe-Coding orchestration by Kamran Jalil—introducing 29 OS-level action engines, AST self-evolution, NVML ctypes telemetry, Sony Bravia Smart IP control, MediaPipe 3D joint kinematics, and automated Inno Setup packaging.
👨‍💻 Author & Architect
Kamran Jalil
AI Agent Architect & Master Vibe Coder
LinkedIn: linkedin.com/in/kamranjalilkhan
GitHub: @Duckierpine3108
Repository: Duckierpine3108/Nexus-AI
<div align="center">
<sub>Engineered with passion for next-generation multimodal artificial intelligence.</sub>
</div>
```