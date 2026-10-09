# Network AI Assistant

Network AI Assistant is a LangGraph/LangChain application for checking and configuring network devices in a GNS3 lab. It supports:

- CLI mode with `python -m src.main`
- Web chat mode with Streamlit using `streamlit run app.py`
- GNS3 topology status checks
- Telnet/SSH device access through Netmiko
- Human approval before risky configuration actions

## Requirements

- Python 3.11 or newer
- GNS3 Server running and reachable from your machine
- A GNS3 project ID
- Network devices configured for Telnet or SSH access
- NVIDIA API key and model name for the LLM

Using a virtual environment is strongly recommended.

## 1. Get The Project

```bash
git clone <your-repository-url>
```

## 2. Create A Virtual Environment

### Windows

```bat
python -m venv venv
venv\Scripts\activate.bat
pip install -r requirements.txt
```

### Linux

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 3. Configure Environment Variables

Create your local `.env` file from the example.

### Windows

```bat
copy .env.example .env
```

### Linux

```bash
cp .env.example .env
```

Open `.env` and fill in your real values:

```env
NVIDIA_API_KEY=your_nvidia_api_key
NVIDIA_MODEL=your_nvidia_model

GNS3_IP=your_gns3_server_ip
GNS3_PORT=3080
PROJECT_ID=your_gns3_project_id

DEFAULT_DEVICE_HOSTNAME=127.0.0.1
DEFAULT_DEVICE_TYPE=cisco_ios_telnet
DEFAULT_DEVICE_USERNAME=admin
DEFAULT_DEVICE_PORT=5000
DEFAULT_DEVICE_PASSWORD=123456

SSH_TIMEOUT=60
SSH_AUTH_TIMEOUT=30
SSH_DELAY_FACTOR=0.5
```

Notes:

- `GNS3_IP` is the IP address of your GNS3 server.
- `GNS3_PORT` is usually `3080`.
- `PROJECT_ID` is the GNS3 project UUID.
- You can find the project ID from the GNS3 API URL or project metadata.

## 4. Configure Devices

Create `config/devices.yaml` from the example.

### Windows

```bat
copy config\devices.yaml.example config\devices.yaml
```

### Linux

```bash
cp config/devices.yaml.example config/devices.yaml
```

Edit `config/devices.yaml` so each device matches your GNS3 console or SSH settings:

```yaml
P1:
  hostname: "127.0.0.1"
  port: 5000
  device_type: "cisco_ios_telnet"
  username: "admin"
  password: "123456"
```

For Telnet console access through GNS3, keep `hostname` as the GNS3 host IP and set `port` to the device console port.

For SSH access, use the device management IP and a Netmiko device type such as:

```yaml
R1:
  hostname: "192.168.1.10"
  port: 22
  device_type: "cisco_ios"
  username: "admin"
  password: "123456"
  secret: "123456"
```

## 5. Start GNS3

Before running the assistant:

1. Start GNS3 Server or GNS3 VM.
2. Open the target project.
3. Start the devices you want the assistant to inspect.
4. Confirm the API works:

```text
http://<GNS3_IP>:<GNS3_PORT>/v2/version
```

Example:

```text
http://127.0.0.1:3080/v2/version
```

## 6. Run The CLI App

From the project root:

### Windows

```bat
venv\Scripts\activate.bat
python -m src.main
```

### Linux

```bash
source venv/bin/activate
python -m src.main
```

Type your request in the terminal. To exit, enter:

```text
q
```

## 7. Run The Streamlit Web App

From the project root:

### Windows

```bat
venv\Scripts\activate.bat
streamlit run app.py
```

### Linux

```bash
source venv/bin/activate
streamlit run app.py
```

Open the URL shown by Streamlit. By default:

```text
http://localhost:8501
```

The web app keeps chat history in the current browser session. Use **Tạo phiên mới** in the sidebar to reset the chat thread.

## Human Approval Flow

Some tools can change device configuration. When the agent needs permission, it will ask for approval.

Reply with:

```text
yes
```

to continue, or:

```text
no
```

to cancel.

## Common Problems

### `ModuleNotFoundError: No module named 'streamlit'`

Install dependencies inside the activated virtual environment:

```bash
pip install -r requirements.txt
```

### `ModuleNotFoundError: No module named 'langchain_nvidia_ai_endpoints'`

Install or refresh the NVIDIA LangChain integration inside the activated virtual environment:

```bash
pip install -r requirements.txt
```

If you installed dependencies before this package was added, run:

```bash
pip install "langchain-nvidia-ai-endpoints>=1.4,<2"
```

### `Không thể kết nối tới GNS3 Server`

Check:

- GNS3 Server is running.
- `GNS3_IP`, `GNS3_PORT`, and `PROJECT_ID` are correct in `.env`.
- The project is open in GNS3.
- Your firewall allows access to the GNS3 API port.

### Device login fails

Check:

- Device is running in GNS3.
- Console or SSH port is correct in `config/devices.yaml`.
- `device_type` matches the access method.
- Username, password, and enable secret are correct.

### PowerShell cannot activate venv

Run:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Then activate again:

```powershell
.\venv\Scripts\Activate.ps1
```

### Streamlit protobuf issue on Python 3.14

This project pins:

```text
protobuf==7.35.1
```

If Streamlit fails while importing protobuf, reinstall dependencies in a fresh virtual environment:

```bash
pip install --force-reinstall -r requirements.txt
```

## Project Structure

```text
src/
  app.py                         Streamlit web chat app
  main.py                        CLI entry point
  core/                          GNS3 and device connection settings
  network_agnets/
    agents/                      LangGraph agents
    graph/                       Workflow and state
    tools/                       Network tools
  utils/                         Logging, console output, helper functions

config/
  devices.yaml.example           Example device inventory

docs/
  configure.txt                  Example device configuration

requirements.txt                 Python dependencies
.env.example                     Environment variable template
```

## Quick Start

Linux:

```bash
cp .env.example .env
cp config/devices.yaml.example config/devices.yaml
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Windows CMD:

```bat
copy .env.example .env
copy config\devices.yaml.example config\devices.yaml
py -3 -m venv venv
venv\Scripts\activate.bat
pip install -r requirements.txt
streamlit run app.py
```
