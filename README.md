<div align="center">

# ⚡ NEXUS AI
### Autonomous Multimodal Desktop Operating Agent & Holographic OS

[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Gemini Live 2.5](https://img.shields.io/badge/Gemini_Live-2.5_Flash-8E75B2?style=for-the-badge&logo=googlebard&logoColor=white)](https://deepmind.google/technologies/gemini/)
[![Platform Windows](https://img.shields.io/badge/Platform-Windows_10%20%7C%2011-0078D6?style=for-the-badge&logo=windows&logoColor=white)](https://www.microsoft.com/windows)
[![Release v1.0.0](https://img.shields.io/badge/Release-v1.0.0-00C853?style=for-the-badge&logo=github)](https://github.com/Duckierpine3108/Nexus-AI/releases)
[![License](https://img.shields.io/badge/License-MIT-orange?style=for-the-badge)](LICENSE)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Kamran_Jalil-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/kamranjalilkhan/)

<br />

> **NEXUS AI** is an ironclad, local desktop operating system assistant engineered for Windows. Powered by Google's native bi-directional **Gemini 2.5 Flash Audio API**, offline **Vosk Kaldi** neural wake engines, and a live reactive **3D holographic avatar**, it acts as a true OS co-pilot. It answers WhatsApp calls, automates multi-browser tasks, manages Steam and Epic Games libraries, executes autonomous coding workflows, and processes complex multi-format files in real time.

<br />

---

</div>

## 📸 Interface Preview

<div align="center">
  <img src="assets/nexus_ui_preview.png" alt="NEXUS AI Interface" width="850" style="border-radius: 10px; box-shadow: 0px 4px 20px rgba(0, 255, 255, 0.2);" />
  <p><i>Real-time 3D reactive avatar with audio-reactive quantum core, live system telemetry, and initialization modal.</i></p>
</div>

---

## 💡 Why NEXUS AI?

Traditional conversational AI assistants live in isolated browser tabs or lightweight text chat windows. They lack direct operating system integration, low-latency duplex voice pipelines, and deep hardware control. 

**NEXUS AI bridges this gap** by operating as a resident background service on Windows that directly orchestrates native applications, monitors system resources, controls web browsers, and manages communications through low-latency voice and function-calling pipelines.

---

## 🚀 Architectural Superpowers

### 1. 📞 Full WhatsApp Desktop Telephony & Agent
NEXUS directly interfaces with and automates the native WhatsApp Desktop application:
* **Voice & Video Calling:** Initiates voice and video calls (`whatsapp_call`), answers incoming calls (`whatsapp_accept_call`), and cleanly disconnects on voice command.
* **Smart Call Decline with Auto-SMS:** Declines calls and immediately dispatches a custom natural-language explanation to the caller via chat (`whatsapp_decline_call`).
* **Incoming Ring Radar:** A background listener continuously detects live desktop call rings, maximizes master system volume, and alerts the user with urgency.
* **Live File & Screenshot Dispatch:** Captures active desktop displays or selects local target files and delivers them directly into any contact's WhatsApp conversation thread (`whatsapp_send_screenshot`, `whatsapp_send_file`).

### 2. 🎮 Steam & Epic Games Automated Fleet Manager
Engineered specifically for power users and gamers:
* **Background Game Updates:** Checks update statuses and triggers downloads for both Steam and Epic Games titles (`game_updater`).
* **Nightly Scheduling:** Schedules heavy game installations or patches during off-peak hours (e.g., at 3:00 AM).
* **Auto-Shutdown on Finish:** Automatically powers down the computer once your game downloads and updates are 100% complete.

### 3. 📂 Universal 22-Action File Intelligence Engine
A complete multi-format file processing suite (`file_processor.py`) that accepts and analyzes files on disk:
* **Document Extraction:** Converts PDFs to Word documents (`to_word`), extracts text, and summarizes lengthy reports.
* **Media Intelligence:** Extracts audio tracks from video files (`extract_audio`), trims media segments (`trim`), and captures specific video frame timestamps (`extract_frame`).
* **Data Processing:** Analyzes CSV/Excel spreadsheets, computes statistics, filters rows based on conditions, and converts structured JSON to CSV.
* **OS File Management:** Auto-organizes cluttered Desktops into dated archives (`organize_desktop`), performs regex file searches, audits large files, and monitors disk storage (`file_controller.py`).

### 4. 🌐 Multi-Browser Web Automation Engine
Full browser automation powered by Playwright and native system hooks (`browser_control.py`):
* **Universal Multi-Browser Driver:** Controls Chrome, Edge, Firefox, Brave, and Opera GX simultaneously.
* **Deep Interaction Suite (20 Sub-Actions):** Handles form filling, smart element clicking, text scraping, multi-tab orchestration, and private/incognito workflows.

### 5. 💻 Autonomous Dev Agent & Self-Healing Code Runner
* **Multi-File Scaffolding:** Plans, writes, and builds complete software projects from a single natural-language prompt (`dev_agent.py`).
* **Auto-Dependency Resolution:** Automatically detects missing Python libraries, installs them via pip, opens the project in VS Code, and executes code while self-healing runtime traceback errors.

### 6. 🧬 3D Holographic Avatar & Floating Desktop Companion
* **Phoneme-Driven Viseme Lip-Sync:** Translates incoming audio energy and phonemes into real-time 3D facial movements on a custom head mesh (`head.glb`).
* **Quantum Arc Core:** Visualizes AI thinking, listening, and standby states through an animated energy sphere.
* **Detachable Companion Widget:** Toggle between a full-screen holographic terminal and an unobtrusive floating companion.

### 7. ⚡ Dual-Engine Audio: Offline Vosk + Gemini 2.5 Live
* **Privacy-First Offline Gate:** Vosk Kaldi offline speech engine listens locally for *"Hey Nexus"* or *"Computer"*. Zero ambient room audio is sent to the cloud until triggered.
* **Full-Duplex Duplex Speech:** Direct 16kHz input / 24kHz output streaming with instant barge-in / interruption support.
* **DSP Analog Pre-Amp Booster:** Custom digital signal processing applies a 3.5x volume multiplier and smooth `tanh` saturation curves to eliminate distortion.

### 8. 🔒 Encrypted Web Dashboard & Mobile Relay
* **Local SSL Command Server:** Encrypted FastAPI/Uvicorn server secured with self-signed TLS/SSL certificates (`jarvis.crt`).
* **Mobile Audio Bridge:** Pair any smartphone via QR code auto-login to route mobile microphone audio directly into NEXUS AI from across the room.

---

## 🛠️ System Architecture

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
 │         Google Gemini 2.5 Flash Native Audio API          │
 │              Full-Duplex Bi-directional PCM               │
 └─────────────────────────────┬─────────────────────────────┘
                               │
                (Real-time Function Calling)
                               ▼
 ┌───────────────────────────────────────────────────────────┐
 │            NEXUS CORE TOOL DISPATCHER                     │
 ├─────────────────┬─────────────────┬───────────────────────┤
 │ WhatsApp Suite  │ Browser Agent   │ Steam & Epic Updater  │
 │ - Voice/Video   │ - Playwright    │ - Nightly Scheduling  │
 │ - Smart Decline │ - 5 Browsers    │ - Auto-Shutdown       │
 ├─────────────────┼─────────────────┼───────────────────────┤
 │ Dev Agent       │ File Engine     │ OS Controller         │
 │ - Multi-file    │ - 22 Sub-actions│ - Hotkeys & Settings  │
 │ - Self-healing  │ - PDF/Media/CSV │ - Desktop Cleaner     │
 └─────────────────┴─────────────────┴───────────────────────┘
                               │
                               ▼
 ┌───────────────────────────────────────────────────────────┐
 │   3D Holographic UI Engine & Dedicated DSP Audio Player   │
 │        Phoneme Viseme Lip-Sync & Quantum Arc Core         │
 └───────────────────────────────────────────────────────────┘
```

---

## 📊 Technical Feature Matrix

| Subsystem | Tool / Module | Underlying Engine | Verified Capabilities |
| :--- | :--- | :--- | :--- |
| **Communication** | `whatsapp_controller` | Win32 / Native UI Automation | Voice/video calls, call decline with SMS, file & screenshot delivery |
| **Gaming** | `game_updater` | Steam CLI & Epic Hooks | Background game updates, install scheduling, auto-shutdown on finish |
| **File Intelligence** | `file_processor` | Native Python / Multi-codec | 22 actions: PDF-to-Word, OCR, CSV analysis, audio/video trim |
| **Web Automation** | `browser_control` | Playwright Driver | 20 actions across Chrome, Edge, Firefox, Brave, Opera GX |
| **Development** | `dev_agent` & `code_helper` | Gemini Code Generation | Multi-file scaffolding, VS Code integration, auto-pip, self-healing |
| **System Control** | `computer_control` | OS Win32 API / PyAutoGUI | Hotkeys, window management, mouse/keyboard automation, clipboard |
| **Audio Core** | `Vosk + Gemini Live` | Kaldi + Google GenAI Live | Offline wake-word detection, full-duplex speech, DSP audio booster |
| **Interface** | `JarvisUI (ui.py)` | PyQt6 / WebEngine / GLB | 3D phoneme lip-sync, quantum arc core, floating companion mode |

---

## 📁 Repository Structure

```text
Nexus-AI/
├── actions/                  # Core capability engines (WhatsApp, Browser, Dev, Games)
│   ├── browser_control.py    # Playwright multi-browser automation
│   ├── computer_control.py   # Windows keyboard/mouse & hotkey automation
│   ├── dev_agent.py          # Autonomous multi-file project builder
│   ├── file_processor.py     # 22-action universal document & media suite
│   ├── game_updater.py       # Steam and Epic Games scheduling & shutdown
│   ├── whatsapp_controller.py# Full WhatsApp calling, messaging & screenshot suite
│   └── ...                   # Additional helper modules
├── assets/                   # Visual assets, UI preview screenshots, logos
├── config/                   # Configuration files, icons, and SSL certificates
├── core/                     # Internal stt, tts, plugin loaders, system prompts
├── dashboard/                # Encrypted FastAPI/Uvicorn server with mobile relay
├── memory/                   # Persistent long-term memory managers
├── model/                    # Offline Vosk speech recognition acoustic model weights
├── plugins/                  # Dynamic plugin architecture directory
├── head.glb                  # 3D holographic avatar mesh
├── index.html                # Web-based UI rendering layer
├── main.py                   # Central orchestration engine and event loop
├── ui.py                     # PyQt6 GUI, 3D phoneme lip-sync & quantum core
├── requirements.txt          # Python dependency specifications
└── README.md                 # Complete technical documentation
```

---

## 📦 Installation & Setup

### Method A: One-Click Windows Installer (Recommended)

1. Download **`nexus_ai_setup.exe`** from the [**NEXUS AI Releases Page**](https://github.com/Duckierpine3108/Nexus-AI/releases/latest).
2. Run the installer and complete the setup wizard.
3. Launch **NEXUS AI** from your Desktop or Start Menu shortcut.
4. Enter your [Google Gemini API Key](https://aistudio.google.com/) on the initialization screen to begin.

### Method B: Run From Source (Developers)

#### Prerequisites
* Windows 10 or 11 (64-bit)
* Python 3.11 installed
* [Microsoft Visual C++ 2015–2022 Redistributable (x64)](https://aka.ms/vs/17/release/vc_redist.x64.exe)

#### Step-by-Step Setup
```bash
# 1. Clone the repository
git clone https://github.com/Duckierpine3108/Nexus-AI.git
cd Nexus-AI

# 2. Create and activate a Python 3.11 virtual environment
python -m venv venv
venv\Scripts\activate

# 3. Install core dependencies
pip install -r requirements.txt

# 4. Launch the application
python main.py
```

---

## 🔒 Security & Privacy Architecture

* **Zero Hardcoded Secrets:** The application contains zero embedded API keys. All credentials are provided at runtime and stored locally in encrypted app configuration.
* **Offline Audio Gating:** Ambient room audio is processed 100% locally by Vosk Kaldi neural weights. Audio is only streamed to cloud models after the local wake word is triggered.
* **Encrypted Remote Control:** Local network dashboard transmissions are secured with end-to-end SSL/TLS encryption.

---

## 🤝 Acknowledgments & Credits

* **Foundational Inspiration:** Portions of the foundational interface structure and concept were inspired by the open-source work of **Faith Make**.
* **NEXUS AI Evolution:** Built upon that foundation, NEXUS AI introduces a custom WhatsApp desktop controller, Steam/Epic Games automated manager, dedicated DSP audio booster, offline Vosk neural wake gating, 22-action file processor, and standalone Windows installer packaging.

---

## 👨‍💻 Author

**Kamran Jalil**  
*AI Engineer & Software Architect*

* **LinkedIn:** [linkedin.com/in/kamranjalilkhan](https://www.linkedin.com/in/kamranjalilkhan/)
* **GitHub:** [@Duckierpine3108](https://github.com/Duckierpine3108)

---

<div align="center">
  <sub>Built with passion for next-generation multimodal artificial intelligence.</sub>
</div>