<h1 align="center">Real-Time AI Screen Translator</h1>

A blazing fast, ultra-lightweight real-time screen and voice translation tool built specifically for gamers. This app allows you to draw a box over any portion of your screen to translate visual text (like dialog boxes or UI), or listen to your live PC game audio and instantly translate spoken dialogue into subtitles directly on your screen without disrupting your gameplay.

<p align="center">
  <a href="https://github.com/Momotz4G/AI-Translation-Realtime/releases/latest">
    <img src="https://img.shields.io/github/v/release/Momotz4G/AI-Translation-Realtime?style=for-the-badge&label=Download%20for%20Windows&color=2ea043&logo=windows" alt="Download for Windows" />
  </a>
</p>

## 📸 Screenshots
<p align="center">
  <img src="assets/1.png" alt="Screenshot 1" width="100%" style="margin-bottom: 20px;">
  <img src="assets/2.png" alt="Screenshot 2" width="100%" style="margin-bottom: 20px;">
  <img src="assets/3.png" alt="Screenshot 3" width="100%" style="margin-bottom: 20px;">
  <img src="assets/1.gif" alt="Live Demo" width="100%">
</p>

> **Note**: Currently, this tool only supports translating from **English to Indonesian**. However, you can use it to translate text anywhere on your screen! It was specifically built and optimized for translating in-game subtitles.

## ✨ Features
- **Zero-Overhead Capture**: Uses `mss` for lightning-fast, physical-pixel accurate region screen capture.
- **Built-in Windows OCR**: Utilizes the native Windows 10/11 OCR (`winsdk`), meaning NO heavy AI models (like Tesseract binaries or PyTorch) are running on your PC. It's incredibly fast and uses almost zero CPU/RAM.
- **🎙️ NEW: Real-Time Voice Translation**: Captures internal PC loopback audio and processes it instantly using Groq's lightning-fast Whisper APIs for near zero-latency voice-to-text translation.
- **🔑 Smart API Key Management**: Safely enter your Groq API keys directly into the UI! Supports entering a comma-separated list of multiple keys for automatic "fallback" rotation when a key runs out of quota.
- **Smart Diffing Engine**: Only translates when the text actually changes, saving bandwidth and preventing API spam.
- **Lightweight Online Translation**: Powered by `deep-translator` routing through free web endpoints, requiring absolutely zero local compute for language processing.
- **Gamer-Friendly UI**: 
  - Sleek, dark-mode Control Panel.
  - **Moveable Overlay**: Freely drag and reposition the translation result window anywhere on your screen.
  - Minimizes quietly to the System Tray.
  - Global **`Ctrl+Alt+X`** hotkey to instantly stop translation without ever having to Alt-Tab out of your game. *(Note: For this hotkey to work while playing anti-cheat protected games like Wuthering Waves, you must run the app as Administrator).*

## 📋 Requirements
- **OS**: Windows 10 or Windows 11 (required for the native `winsdk` OCR engine and internal PC loopback audio capture).
- **Voice Translation**: A free [Groq API Key](https://console.groq.com/keys) is required to use the Voice Translation feature. (The standard visual OCR feature works completely offline without an API key).

## ⚠️ Disclaimer
1. **OCR**: Translation and text recognition (OCR) accuracy is not 100% perfect. Performance heavily depends on the complexity of the background and the opacity of the text. For the best results, try to scan text that has high contrast against its background (like subtitles with a dark backing).
2. **Voice Translation**: AI transcription from audio is not 100% perfectly accurate. Because the app captures your live audio into small chunks and sends them to Groq's APIs over the internet for processing, you will naturally experience a small 1-2 second delay before the translation appears.

## 🛡️ Is this safe?
**Yes!** 
- **No Heavy Background AI**: We do not run any local LLMs that hog your GPU, battery, or memory.
- **Native OS APIs**: The text recognition relies entirely on the highly optimized OCR engine already built into your Windows operating system.
- **Secure API Key Storage**: Your personal Groq API keys are stored strictly in a local `.env` file on your own computer. They are never transmitted anywhere except directly to Groq's secure official servers.
- **Open Source**: The code is completely transparent. Feel free to inspect `main.py` and the other scripts to see exactly how your data is handled!

## 🚀 Setup & Development (For Forking)

If you want to fork this project, modify the code, or run it directly from the Python source, follow these steps:

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/AI-Translation-Realtime.git
   cd AI-Translation-Realtime
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   *(Note: This project requires Windows 10 or 11 due to the `winsdk` dependency).*

3. **Run the App**:
   ```bash
   python main.py
   ```

## 📦 How to Build the Standalone `.exe`

If you want to compile your modified code into a single, highly compressed `.exe` file to share with friends who don't have Python installed, you can use PyInstaller.

1. **Install PyInstaller**:
   ```bash
   pip install pyinstaller
   ```

2. **Run the Optimized Build Command**:
   We've already configured an optimized PyInstaller `.spec` file that aggressively excludes bulky unused libraries (like PyQt6 web modules) to keep the executable lightweight. Simply run:
   
   ```bash
   pyinstaller --clean RealtimeTranslation_Compact.spec
   ```

3. **Find your App**:
   Once finished, your new standalone app will be located in the `dist/` folder as `RealtimeTranslation_Compact.exe`. You can drag and drop this single file to anyone!

## 🔒 Privacy Policy
This application operates strictly as a local overlay. **We do not collect, store, or transmit any personal data, screenshots, or keystrokes.** The screen region you select is processed locally by Windows OCR, and only the extracted text string is temporarily sent to Google Translate's free web endpoint for translation.

For Voice Translation, the audio detector captures your PC loopback audio directly into **RAM**—no audio files are ever saved or written to your hard drive. These small, temporary RAM chunks are sent directly to Groq via their secure API for processing and instantly wiped. Absolutely no telemetry or data is sent to any third-party tracking servers.

## 📝 License
MIT License
