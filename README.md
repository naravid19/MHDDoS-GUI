<!-- Improved compatibility of back to top link: See: https://github.com/othneildrew/Best-README-Template/pull/73 -->
<a id="readme-top"></a>

<!-- PROJECT SHIELDS -->
<div align="center">
  <a href="https://github.com/naravid19/MHDDoS-GUI/graphs/contributors">
    <img src="https://img.shields.io/github/contributors/naravid19/MHDDoS-GUI.svg?style=for-the-badge" alt="Contributors">
  </a>
  <a href="https://github.com/naravid19/MHDDoS-GUI/network/members">
    <img src="https://img.shields.io/github/forks/naravid19/MHDDoS-GUI.svg?style=for-the-badge" alt="Forks">
  </a>
  <a href="https://github.com/naravid19/MHDDoS-GUI/stargazers">
    <img src="https://img.shields.io/github/stars/naravid19/MHDDoS-GUI.svg?style=for-the-badge&color=yellow" alt="Stargazers">
  </a>
  <a href="https://github.com/naravid19/MHDDoS-GUI/issues">
    <img src="https://img.shields.io/github/issues/naravid19/MHDDoS-GUI.svg?style=for-the-badge&color=purple" alt="Issues">
  </a>
  <a href="https://github.com/naravid19/MHDDoS-GUI/blob/master/LICENSE">
    <img src="https://img.shields.io/github/license/naravid19/MHDDoS-GUI.svg?style=for-the-badge" alt="License">
  </a>
</div>

<!-- PROJECT LOGO -->
<br />
<div align="center">
  <a href="https://github.com/naravid19/MHDDoS-GUI">
    <img src="https://img.icons8.com/color/512/globe--v1.png" alt="Logo" width="80" height="80">
  </a>

<h3 align="center">MHDDoS Professional v1.2.1</h3>

  <p align="center">
    A Modern, High-Performance Web & Desktop GUI for the renowned MHDDoS Script.
    <br />
    <a href="https://github.com/naravid19/MHDDoS-GUI"><strong>Explore the docs »</strong></a>
    <br />
    <br />
    <a href="https://github.com/naravid19/MHDDoS-GUI">View Demo</a>
    &middot;
    <a href="https://github.com/naravid19/MHDDoS-GUI/issues/new?labels=bug">Report Bug</a>
    &middot;
    <a href="https://github.com/naravid19/MHDDoS-GUI/issues/new?labels=enhancement">Request Feature</a>
  </p>
</div>

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
    <li><a href="#roadmap">Roadmap</a></li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
    <li><a href="#acknowledgments">Acknowledgments</a></li>
  </ol>
</details>

<!-- ABOUT THE PROJECT -->
## About The Project

[![Product Name Screen Shot](images/screenshot.png)](https://github.com/naravid19/MHDDoS-GUI)

**MHDDoS-GUI** is an advanced evolution of the original [MatrixTM/MHDDoS](https://github.com/MatrixTM/MHDDoS) script, now equipped with a stunning, highly optimized graphical user interface. Designed with premium dark mode aesthetics and built for absolute performance, this project provides both a Web Dashboard and a standalone Desktop Application to launch, monitor, and manage up to 59 distinct DDoS attack methods.

### Features

*   **Deep TLS/JA3 Impersonation**: Integrated `curl-cffi` to provide native-level browser fingerprinting. The engine mimics exact TLS handshakes (JA3) of specific browsers, bypassing advanced anti-bot mitigations.
*   **HTTP/3 (QUIC) Support**: High-efficiency `HTTP3` method utilizing the `httpx` and `h3` libraries to bypass modern WAFs via QUIC-based traffic.
*   **True Distributed C2**: Decentralized architecture that shares bypassed Cloudflare credentials (`cf_clearance`) across the entire fleet in real-time.
*   **Combat Impact Dashboard**: Real-time visualization of "Actual Hits" (Fidelity) and target response distribution (2xx/4xx/5xx) using status code sampling.
*   **Precision Cloudflare Bypass**: Advanced `solve_cf` engine utilizing `nodriver`, coordinate-based Turnstile clicking, and WebGL hardware masking.
*   **AsyncIO Core Engine**: Completely asynchronous Layer 7 flooding engine (`asyncio` + `aiohttp`) with centralized session management via `AsyncHTTPManager`.
*   **Operations History & Analytics**: Persistent SQLite-backed history tracking with interactive time-series charts (PPS/BPS/Latency).
*   **AI Smart Bypass (Machine Learning)**: Adaptive heuristic feedback loop that analyzes WAF responses and dynamically tweaks User-Agents and headers.
*   **Enterprise-Grade UI**: Fully responsive, data-dense dark mode GUI with full ARIA-compliant accessibility and "Glassmorphism 2.0" aesthetics.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### Built With

*   [![Python][Python-shield]][Python-url]
*   [![FastAPI][FastAPI-shield]][FastAPI-url]
*   [![TailwindCSS][Tailwind-shield]][Tailwind-url]
*   [![Chart.js][ChartJS-shield]][ChartJS-url]
*   [![Playwright][Playwright-shield]][Playwright-url]

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- GETTING STARTED -->
## Getting Started

To get a local copy up and running, follow these simple steps.

### Prerequisites

Ensure you have Python 3.11+ installed on your system.
*   Python 3
    ```sh
    python --version
    ```

### Installation

1.  Clone the repo
    ```sh
    git clone https://github.com/naravid19/MHDDoS-GUI.git
    ```
2.  Install required Python packages
    ```sh
    pip install -r requirements.txt
    ```
3.  Install advanced browser engines
    ```sh
    playwright install chromium
    ```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- USAGE EXAMPLES -->
## Usage

### 1. Web Dashboard Mode (Recommended)
Launch the backend server and access the tactical interface via browser (port 8000).
```sh
python web_gui.py --force
```

### 2. Desktop Application Mode
Start the GUI in a standalone application window.
```sh
python desktop_gui.py
```

### 3. Distributed Worker Mode
Connect multiple nodes to your master API for collective operations.
```sh
python worker.py --master http://YOUR_MASTER_IP:8000 --token SECRET_TOKEN
```

### Supported Methods
**Layer 7**: `GET`, `POST`, `IMPERSONATE`, `HTTP3`, `CFB`, `CFBUAM`, `BYPASS`, `BOMB`, `KILLER`, `TOR`, etc. (Total 26)  
**Layer 4**: `TCP`, `UDP`, `SYN`, `MCPE`, `DNS`, `VSE`, `MCBOT`, etc. (Total 21)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- ROADMAP -->
## Roadmap

- [x] True Distributed Bypass Token Sync
- [x] Real-time Combat Impact (Fidelity) Analysis
- [x] Deep TLS/JA3 Fingerprinting (`IMPERSONATE`)
- [x] HTTP/3 (QUIC) Protocol Support
- [ ] Automated Infrastructure Recon (Asset Discovery)
- [ ] Distributed Load Balancing across Global Fleet

See the [open issues](https://github.com/naravid19/MHDDoS-GUI/issues) for a full list of proposed features (and known issues).

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- CONTRIBUTING -->
## Contributing

Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

1.  Fork the Project
2.  Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3.  Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4.  Push to the Branch (`git push origin feature/AmazingFeature`)
5.  Open a Pull Request

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- LICENSE -->
## License

Distributed under the Unlicense License. See `LICENSE` for more information.

> [!CAUTION]
> This tool is meant for educational purposes and authorized network stress testing ONLY. Testing infrastructure without full legal authorization is a cybercrime.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- CONTACT -->
## Contact

Project Link: [https://github.com/naravid19/MHDDoS-GUI](https://github.com/naravid19/MHDDoS-GUI)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- ACKNOWLEDGMENTS -->
## Acknowledgments

*   [MatrixTM / MHDDoS](https://github.com/MatrixTM/MHDDoS) - Core engine foundation.
*   [Othneil Drew / Best-README-Template](https://github.com/othneildrew/Best-README-Template) - Structural template.
*   [curl-cffi](https://github.com/yifeikong/curl-cffi) - TLS impersonation capabilities.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- MARKDOWN LINKS & IMAGES -->
[Python-shield]: https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white
[Python-url]: https://www.python.org/
[FastAPI-shield]: https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white
[FastAPI-url]: https://fastapi.tiangolo.com/
[Tailwind-shield]: https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white
[Tailwind-url]: https://tailwindcss.com/
[ChartJS-shield]: https://img.shields.io/badge/Chart.js-FF6384?style=for-the-badge&logo=chartdotjs&logoColor=white
[ChartJS-url]: https://www.chartjs.org/
[Playwright-shield]: https://img.shields.io/badge/Playwright-2EAD33?style=for-the-badge&logo=playwright&logoColor=white
[Playwright-url]: https://playwright.dev/
