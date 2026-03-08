<a id="readme-top"></a>

<!-- PROJECT LOGO -->
<br />
<div align="center">
  <a href="https://github.com/naravid19/MHDDoS-GUI">
    <img src="https://img.icons8.com/color/512/globe--v1.png" alt="Logo" width="80" height="80">
  </a>

<h3 align="center">MHDDoS Professional v1.1.1</h3>

  <p align="center">
    A Modern, High-Performance Web & Desktop GUI for the renowned MHDDoS Script.
    <br />
    <br />
    <a href="https://github.com/naravid19/MHDDoS-GUI/issues/new?labels=bug">Report Bug</a>
    &middot;
    <a href="https://github.com/naravid19/MHDDoS-GUI/issues/new?labels=enhancement">Request Feature</a>
  </p>
</div>

<!-- SHIELDS -->
<div align="center">
  <a href="#"><img alt="MH-DDoS forks" src="https://img.shields.io/github/forks/naravid19/MHDDoS-GUI?style=for-the-badge"></a>
  <a href="#"><img alt="MH-DDoS stars" src="https://img.shields.io/github/stars/naravid19/MHDDoS-GUI?style=for-the-badge&color=yellow"></a>
  <a href="https://github.com/naravid19/MHDDoS-GUI/issues"><img alt="Issues" src="https://img.shields.io/github/issues/naravid19/MHDDoS-GUI?color=purple&style=for-the-badge"></a>
</div>

<br />

> [!CAUTION]
> **Please Don't Attack websites without the owner's consent.**

<br />

<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
      <ul>
        <li><a href="#features">Features</a></li>
        <li><a href="#built-with">Built With</a></li>
      </ul>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#methods">Supported Methods</a></li>
    <li><a href="#disclaimer">Disclaimer</a></li>
    <li><a href="#acknowledgments">Acknowledgments</a></li>
  </ol>
</details>

<br />

<!-- ABOUT THE PROJECT -->

## About The Project

[![Product Name Screen Shot][product-screenshot]](https://github.com/naravid19/MHDDoS-GUI)

**MHDDoS-GUI** is an advanced evolution of the original [MatrixTM/MHDDoS](https://github.com/MatrixTM/MHDDoS) script, now equipped with a stunning, highly optimized graphical user interface. Designed with premium glassmorphism aesthetics and built for absolute performance, this project provides both a Web Dashboard and a standalone Desktop Application to launch, monitor, and manage up to 47 distinct DDoS attack methods.

### Features

- **Engine Optimization Dimension (v1.1.2)**: Advanced features for maximizing attack capabilities.
    - **Dynamic Worker Scaling**: Automatically scales the number of active threads based on the host machine's CPU/RAM resources to ensure peak performance without crashing the system.
    - **Smart RPC Rotation**: Enhanced `--smart` logic dynamically randomizes RPC values, User-Agents, and headers when target mitigation (latency spikes, 403s) is detected.
- **Log Intensity Controller (v1.1.1)**: Integrated a multi-tier verbosity management system. Users can toggle between **MINIMAL**, **TACTICAL**, and **VERBOSE** modes to filter engine output based on technical requirements (Diagnostics vs. Status).
- **Advanced Proxy Ecosystem (v1.1.1)**: A self-healing, protocol-aware resource management system.
    - **Non-Lethal Stability Scoring**: Real-time node failure tracking with dynamic weight penalties. Proxies are never discarded; instead, traffic is mathematically shifted toward high-uptime "Elite-Tier" proxies.
    - **Protocol-Specific Validation**: Explicit SSL/TLS handshake verification for Layer 7 attacks and SOCKS5 UDP Associate testing for Layer 4 UDP floods.
    - **Autonomous Sourcing**: Heuristic AI that automatically scrapes global fallback matrices when the active pool is depleted mid-attack.
- **Intelligence Recon Matrix (v1.0.8)**: A sophisticated reconnaissance suite integrated directly into the dashboard.
    - **Auto-Method Recommendation**: Signature-based WAF detection (Cloudflare, DDoS-Guard, Sucuri, etc.) that automatically suggests the most effective attack method.
    - **Visual Geo-IP Mapping**: Real-time server location tracking using integrated Leaflet.js maps.
    - **Surface Explorer**: Automated subdomain discovery to identify unprotected endpoints and vulnerable infrastructure.
- **Tactical Proxy Efficiency Reporting (v1.0.7)**: Detailed reporting of "Elite-Tier" vs "Total Assets Synchronized" for professional situational awareness.
- **Enhanced DNPR Feedback (v1.0.7)**: High-signal tactical terminology integrated into the Dynamic Proxy Rotation (DNPR) engine.
- **Auto-Harvest Optimization (v1.0.7)**: Refined harvest logic for improved synchronization between manual requests and tactical engine logs.
- **Tactical Recon Tools (v1.0.6)**: Built-in suite of diagnostic tools including **ICMP Ping**, **HTTP Status Checker**, and **Geo-IP Recon**.
- **Config Modal Validation (v1.0.6)**: Built-in safety checks for Proxy Auto-Harvest configurations.
- **Local File Auto-Harvest Support (v1.0.6)**: Natively supports reading proxy sources from absolute local file paths.
- **Hacker-Professional Hybrid UI (v1.0.6)**: Redesigned dashboard using Fira Sans and Fira Code typography.
- **Enhanced Log Filtering (v1.0.6)**: Granular log categories (`ALL`, `ATTACK`, `SYSTEM`, `ERROR`) with an optimized filtering engine.
- **Launcher Resilience (v1.0.6)**: Upgraded backend synchronization with health checks and port conflict detection.
- **Premium Enterprise Overhaul (v1.0.5)**: Re-engineered UI with **Glassmorphism 2.0** aesthetics and a refined Slate-950 color palette.
- **System Health Matrix**: Real-time header-level monitoring of engine status, proxy sync health, and encryption protocol stability.
- **Dynamic Proxy Rotation (v1.0.4)**: Integrated thread-safe proxy hot-swapping with configurable auto-refresh intervals (15/30/60m).
- **Smoothed Real-time Visualization**: Upgraded metric charts with cubic interpolation and area-fill gradients.
- **Infrastructure Analytics**: New diagnostics bar displaying pipeline status, encryption levels, and real-time kernel telemetry.
- **Dual Architecture**: Run as a responsive Web Dashboard or a native Desktop App.
- **Premium UX/UI**: Designed using Tailwind CSS for a modern experience with CRT scanline overlays.
- **Full Method Parity**: Categorized support for all 47 attack methods + 10 utility/control commands (57 total).
- **Remote Proxy Support**: Seamlessly stream massive proxy lists from remote URLs directly into engine memory.
- **Auto-Saving Settings**: Persists all tactical configurations across sessions using browser LocalStorage.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### Built With

- [![Python][Python.org]][Python-url]
- [![FastAPI][FastAPI.com]][FastAPI-url]
- [![TailwindCSS][Tailwind.com]][Tailwind-url]
- [![Chart.js][Chart.js.org]][Chart-url]
- [![JavaScript][JS.org]][JS-url]

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- GETTING STARTED -->

## Getting Started

Follow these simple steps to get your local environment set up.

### Prerequisites

Ensure you have Python 3 installed on your system.

- Python 3
  ```sh
  python --version
  ```

### Installation

1. Clone the repository
   ```sh
   git clone https://github.com/naravid19/MHDDoS-GUI.git
   ```
2. Navigate to the directory
   ```sh
   cd MHDDoS-GUI
   ```
3. Install the required Python packages
   ```sh
   pip install -r requirements.txt
   ```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- USAGE -->

## Usage

There are two primary ways to run the MHDDoS-GUI depending on your preference.

**1. Desktop Application Mode (Recommended)**  
Launch the GUI in a standalone application window for a seamless desktop experience:

```sh
python desktop_gui.py
```

**2. Web Dashboard Mode**  
Start the backend server and open the UI in your default web browser (accessible locally on port `8000`):

```sh
python web_gui.py
```

### Manual Commands (CLI)

You can still use the core script directly from the terminal if needed:

- Layer 7: `python start.py <method> <url> <socks_type> <threads> <proxylist> <rpc> <duration>`
- Layer 4 Normal: `python start.py <method> <ip:port> <threads> <duration>`

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- METHODS -->

## Supported Methods

MHDDoS-GUI supports 47 methods. Here is a brief overview:

**Layer 7**  
`GET` | `POST` | `OVH` | `RHEX` | `STOMP` | `STRESS` | `DYN` | `DOWNLOADER` | `SLOW` | `HEAD` | `NULL` | `COOKIE` | `PPS` | `EVEN` | `GSB` | `DGB` | `AVB` | `BOT` | `APACHE` | `XMLRPC` | `CFB` | `CFBUAM` | `BYPASS` | `BOMB` | `KILLER` | `TOR`

**Layer 4 (Normal & Amplification)**  
`TCP` | `UDP` | `SYN` | `OVH-UDP` | `CPS` | `ICMP` | `CONNECTION` | `VSE` | `TS3` | `FIVEM` | `FIVEM-TOKEN` | `MEM` | `NTP` | `MCBOT` | `MINECRAFT` | `MCPE` | `DNS` | `CHAR` | `CLDAP` | `ARD` | `RDP`

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- DISCLAIMER -->

## Disclaimer

> [!WARNING]
> This graphical representation and the underlying script represent a powerful network testing utility.
> The tool is meant for educational purposes and authorized network stress testing ONLY. Testing infrastructure without full legal authorization constitutes a cybercrime. The author is not responsible for any misuse.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- ACKNOWLEDGMENTS -->

## Acknowledgments

Huge thanks to the original creators and the open-source community that made this tool possible:

- [MatrixTM / MHDDoS](https://github.com/MatrixTM/MHDDoS) - The original powerful core script.
- [Othneil Drew / Best-README-Template](https://github.com/othneildrew/Best-README-Template) - For the amazing structural template.
- [React Icons](https://react-icons.github.io/react-icons/)
- [Tailwind CSS Components](https://tailwindui.com/)
- [FastAPI Framework](https://fastapi.tiangolo.com/)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- MARKDOWN LINKS & IMAGES -->

[Python.org]: https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white
[Python-url]: https://www.python.org/
[FastAPI.com]: https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white
[FastAPI-url]: https://fastapi.tiangolo.com/
[React.js]: https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB
[React-url]: https://reactjs.org/
[Tailwind.com]: https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white
[Tailwind-url]: https://tailwindcss.com/
[Vite.js]: https://img.shields.io/badge/Vite-646CFF?style=for-the-badge&logo=vite&logoColor=white
[Vite-url]: https://vitejs.dev/
[Chart.js.org]: https://img.shields.io/badge/Chart.js-FF6384?style=for-the-badge&logo=chartdotjs&logoColor=white
[Chart-url]: https://www.chartjs.org/
[JS.org]: https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black
[JS-url]: https://developer.mozilla.org/en-US/docs/Web/JavaScript
[product-screenshot]: images/screenshot.png
