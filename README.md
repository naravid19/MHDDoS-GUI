<a id="readme-top"></a>

<!-- PROJECT LOGO -->
<br />
<div align="center">
  <a href="https://github.com/naravid19/MHDDoS-GUI">
    <img src="https://img.icons8.com/color/512/globe--v1.png" alt="Logo" width="80" height="80">
  </a>

<h3 align="center">MHDDoS-GUI v1.0.1</h3>

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

**MHDDoS-GUI** is an advanced evolution of the original [MatrixTM/MHDDoS](https://github.com/MatrixTM/MHDDoS) script, now equipped with a stunning, highly optimized graphical user interface. Designed with premium glassmorphism aesthetics and built for absolute performance, this project provides both a Web Dashboard and a standalone Desktop Application to launch, monitor, and manage up to 57 distinct DDoS attack methods.

Say goodbye to complex console commands. Now you can select proxies, tune threads, choose your Layer 4 or Layer 7 attack methods, and view real-time log outputs all through an incredibly intuitive and visually striking dashboard.

### Features

- **Dual Architecture**: Run as a responsive Web Dashboard or a native Desktop App.
- **Premium UX/UI**: Designed using Tailwind CSS and React for a modern, dark-theme `glassmorphism` experience.
- **Real-time Console**: Live streaming of attack logs directly into the UI via WebSockets.
- **Easy Configurability**: Intuitive controls for methods, threads, proxies, reflectors, and duration.
- **Remote Proxy Support**: Streamline proxy logic by importing massive proxy lists straight from `http://` / `https://` URLs seamlessly into memory. The core now reliably logic-scrapes endpoints with custom Regex mapping to ensure no lists are dropped.
- **Smart Contextual UI**: Dynamically shows or hides relevant Input Fields (like Proxies, Reflectors, and RPC) depending on whether a Layer 4 or Layer 7 attack method is selected.
- **Auto-Saving Settings**: Retains your configuration (Target, Method, Threads, etc.) across sessions using browser LocalStorage.
- **Full Compatibility and Stable**: Supports all 57 attack layers (L4 and L7) from the original MHDDoS core with enhanced internal handling for error-free multi-threading.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### Built With

- [![Python][Python.org]][Python-url]
- [![FastAPI][FastAPI.com]][FastAPI-url]
- [![React][React.js]][React-url]
- [![TailwindCSS][Tailwind.com]][Tailwind-url]
- [![Vite][Vite.js]][Vite-url]

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

MHDDoS-GUI supports 57 methods. Here is a brief overview:

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
[product-screenshot]: images/screenshot.png
