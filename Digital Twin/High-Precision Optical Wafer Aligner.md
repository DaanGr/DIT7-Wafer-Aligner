## 1. System Overview & Objective

**Subsystem Role:** Process Station (Alignment). **Objective:** To receive a semiconductor wafer (150mm/200mm/300mm) placed with random orientation and eccentricity, and mechanically re-orient it to a specific "Notch/Flat" position and center point to prepare it for subsequent lithography or inspection processes.

**Core Challenge:** The Digital Twin must demonstrate the balance between **Throughput** (high-speed rotation) and **Stability** (preventing wafer slip via vacuum physics).

## 2. Operational Concept
The system operates as a "Turn-Table" station integrating motion control and optical sensing.
1. **Ingress:** The external Transport Robot (Classmate) places the wafer on the Aligner Chuck.
2. **Capture:** The Aligner activates the vacuum circuit to secure the wafer.
3. **Measurement Scan:** The chuck rotates 360°. A fixed Through-Beam Laser Sensor measures the wafer edge position.
    - _Data Point:_ Variations in edge position indicate eccentricity (off-center).
    - _Data Point:_ A sharp change in edge position indicates the Notch (orientation).
4. **Correction:** The PLC calculates the shortest path to the target angle and rotates the chuck.
5. **Egress:** Vacuum is released, and the system signals readiness for robot pickup.

## 3. Architecture & Technology Stack

### A. Mechanical Design (Siemens NX)
- **Rotary Mechanism:** A Direct-Drive Rotary Stage design (to eliminate gearbox backlash) ensuring positional accuracy < 0.1°.
- **End Effector (Chuck):** A custom multi-zone vacuum chuck designed to accommodate 150, 200, and 300mm diameters.
- **Sensing Hardware:** High-resolution Optical Micrometer (Through-beam configuration) mounted on a linear adjustment rail (or wide-beam sensor) to accommodate varying wafer diameters.
- **Standards Compliance:** Design adheres to **SEMI M1** specifications for wafer notch dimensions.

### B. Automation Logic (TIA Portal)
- **Control Architecture:** State Machine Logic (States: `IDLE`, `CLAMP`, `SCAN`, `CALC`, `POSITION`, `RELEASE`).
- **Algorithm:** Custom "Notch Detection Algorithm" implemented in SCL (Structured Control Language). It captures sensor values into an array during rotation and identifies the index of the Notch.
- **Motion Control:** High-speed Technology Object (TO_Axis) with dynamic acceleration limiting.

### C. Advanced Simulation (FMU Integration)

**Physics Domain:** Multi-body Dynamics / Friction Physics. **Simulation Scenario:** "Wafer Slip Dynamics vs. Acceleration."
- **Problem:** To maximize throughput, the motor must accelerate quickly. However, excessive acceleration overcomes the friction provided by the vacuum, causing the wafer to slip (losing alignment).
- **The FMU Model:** A Python/Modelica model calculating the torque limit based on:
    - **Inputs:** Motor Angular Acceleration (α), Vacuum Pressure (Pvac​), Wafer Mass (m).
    - **Physics:** Ffriction​=μ⋅(Pvac​⋅A) vs. Finertial​=m⋅r⋅α.
    - **Output:** `Slip_Factor` (0.0 to 1.0). If `Slip_Factor > 1.0`, the system triggers a "Position Error" alarm in TIA Portal.

## 4. External Interfaces (System Integration)

To ensure interoperability with the Transport Robot (Classmate's Subsystem), the Digital Twin utilizes the **SEMI E84** handshake protocol simulation:

|Signal Name|Direction|Description|
|---|---|---|
|**TR_REQ**|Input (from Robot)|Robot requests to load a wafer.|
|**READY_TO_LOAD**|Output (to Robot)|Aligner is empty and ready to receive.|
|**BUSY**|Output (to Robot)|Alignment process is currently active.|
|**PROCESS_COMPLETE**|Output (to Robot)|Alignment done, ready for unload.|
## 5. Justification of Design Choice

1. **Why Optical Alignment?** Unlike mechanical alignment (physically pushing the wafer with pins), optical alignment is non-contact (edge-grip only), significantly reducing particle generation—a critical requirement for ISO Class 1 Cleanrooms.
2. **Why FMU for Slip?** Standard kinematic simulations in NX MCD assume "infinite friction" (parts stick together perfectly). Integrating an FMU allows for the simulation of **failure modes**, proving the robustness of the control logic against aggressive tuning parameters.
