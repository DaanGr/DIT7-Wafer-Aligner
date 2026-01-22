# DIT7 Wafer Aligner Digital Twin

## Introduction
This repository contains the Digital Twin implementation of a Wafer Aligner unit, designed for a semiconductor wafer handling system. It integrates mechanical kinematics in Siemens NX, control logic in TIA Portal, and physics simulation via FMU.

For more detailed documentation, see:
- [Wafer Aligner Unit Description](./Wafer%20Aligner.md)

## Dependencies
Ensure the following software is installed and licensed:
*   **Siemens NX 2312** (Mechatronics Concept Designer)
*   **TIA Portal V20**
*   **WinCC V20**
*   **Startdrive V20 SP1**
*   **PLCSIM Advanced V4**

## Project Structure
*   `docs/` - Documentation files.
*   `FMU/` - Functional Mock-up Units and Python build scripts.
*   `PLC Code/` - SCL source files and TIA Portal project (`.ap20`).
*   `Wafer Aligner/` - Siemens NX CAD/MCD files (`.prt`).

## How to Start the Simulation

### 1. Configure PLC Sim Advanced
1.  Start **PLCSIM Advanced V4**.
2.  Set the switch to **PLCSIM Virtual Eth. Adapter**.
3.  Create a new instance with the following settings:
    *   **Instance Name:** `PC_WaferHandling`
    *   **IP Address:** `192.168.0.1`
    *   **Subnet Mask:** `255.255.255.0`
4.  Start the instance.

### 2. Setup TIA Portal
1.  Open **TIA Portal V20**.
2.  Open the project file: `PLC Code/UN_Wafer_Handling_System/UN_Wafer_Handling_System.ap20`.
    *   *Note: If the `.ap20` file is not available, restore the project from `PLC Code/PC_Wafer_Handling_System.zap20`.*
3.  Compile the project to ensure no errors.
4.  Download the project to the `PC_WaferHandling` PLC instance.
5.  Set the PLC to **RUN** mode.

### 3. Setup Siemens NX
1.  Open **Siemens NX 2312**.
2.  Load the master assembly file: `Wafer Aligner/Wafer Aligner.prt`.
3.  Ensure the "Mechatronics Concept Designer" (MCD) application is active.

### 4. Run the Simulation
1.  In Siemens NX, click **Play** to start the MCD simulation.
2.  In TIA Portal, open the **HMI simulation** (or root screen).
3.  On the HMI screen:
    *   Select Wafer Type: **200mm**.
    *   Press the **Start** button.

## Troubleshooting
*   **Connection Issues:** Verify that the PLCSIM Advanced instance name matches exactly (`PC_WaferHandling`) and the IP address is correct.
*   **Signal Mapping:** If signals are not exchanging, check the External Signal Configuration in NX MCD under `MCD_Signals.xml`.