# Hue Shortcut Script

This script allows you to control Philips Hue devices (lights, plugs, etc.) using keyboard shortcuts on Windows. You can configure multiple devices with individual hotkeys, update the Hue API username, and toggle device states. All configuration is stored in a `.env` file.

## Features

- **Interactive Setup:**  
  Configure your Hue Bridge, choose between using an existing Hue API username or automatic registration (by pressing the link button), and add multiple devices with individual hotkeys.

- **Multiple Devices:**  
  Support for configuring multiple devices (lights, plugs, etc.) with separate keyboard shortcuts.

- **Username Update:**  
  Use the `--username` flag to update your Hue API username. The script validates an existing username or performs automatic registration if needed.

- **Configuration Editing:**  
  Use the `--edit` flag to reconfigure your devices interactively.

- **Detailed Logging:**  
  Logs provide detailed troubleshooting information.

## Installation

### Prerequisites

- Python 3.x installed on your system.
- A Philips Hue Bridge and at least one Hue device (light, plug, etc.).

### Creating a Virtual Environment on Windows

1. **Open Command Prompt or PowerShell** and navigate to your project directory.

2. **Create a Virtual Environment:**

    ```bash
    python -m venv venv
    ```

3. **Activate the Virtual Environment:**

    - **Command Prompt:**
    
      ```bash
      venv\Scripts\activate.bat
      ```
    
    - **PowerShell:**
    
      If you encounter a permission error like:
      
      ```
      running scripts is disabled on this system. For more information, see about_Execution_Policies at ...
      ```
      
      Run the following command in PowerShell (as Administrator or for the current user):
      
      ```powershell
      Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
      ```
      
      Then activate the virtual environment:
      
      ```powershell
      .\venv\Scripts\Activate.ps1
      ```

### Installing Required Packages

With the virtual environment activated, install the required packages:

```bash
pip install requests python-dotenv keyboard
