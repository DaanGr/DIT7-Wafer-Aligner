# WAFER ALIGNER FMU IMPLEMENTATION GUIDE

## Document Purpose
This document provides a step-by-step guide for developing a Functional Mock-up Unit (FMU) for the High-Precision Optical Wafer Aligner Digital Twin. The FMU will implement the **Wafer Slip Dynamics** physics model as described in the system specification.

---

## 1. FMU TECHNICAL BACKGROUND

### 1.1 What is an FMU?
A **Functional Mock-up Unit (FMU)** is a standardized simulation component defined by the **FMI (Functional Mock-up Interface)** standard. It enables model exchange and co-simulation between different simulation tools.

**Key Components of an FMU:**
- **modelDescription.xml**: Defines inputs, outputs, parameters, and metadata
- **Binary files**: Platform-specific compiled code (.dll for Windows, .so for Linux)
- **Resources folder**: Additional files (icons, documentation, data)

### 1.2 FMI Standard Variants

| Variant | Description | Use Case |
|---------|-------------|----------|
| **Model Exchange (ME)** | Provides model equations; importing tool handles integration | Tight integration with master simulator's solver |
| **Co-Simulation (CS)** | Contains its own solver; exchanges data at communication points | Stand-alone execution with defined time steps |

**For this project:** We will implement **FMI 2.0 for Co-Simulation** because:
1. The slip dynamics model is independent and self-contained
2. Co-simulation is easier to integrate with Siemens NX MCD
3. It allows stand-alone testing before integration

### 1.3 FMU Structure
```
WaferSlipDynamics.fmu (ZIP archive)
├── modelDescription.xml       # FMI interface definition
├── binaries/
│   ├── win64/
│   │   └── WaferSlipDynamics.dll
│   └── linux64/
│       └── WaferSlipDynamics.so
└── resources/
    ├── model.png              # Icon (optional)
    └── documentation/
```

---

## 2. WAFER SLIP DYNAMICS MODEL SPECIFICATION

### 2.1 Physical Problem
The wafer aligner system must balance two competing requirements:
- **High Throughput**: Fast acceleration to minimize cycle time
- **Stability**: Prevent wafer slippage on the vacuum chuck

**Physics Domain:** Multi-body dynamics with friction modeling

### 2.2 Model Equations

#### Input Variables
| Variable | Symbol | Unit | Description | Source in TIA Portal |
|----------|--------|------|-------------|---------------------|
| Angular Acceleration | `alpha` (α) | rad/s² | Spindle angular acceleration | Derivative of `EM_Spindle` velocity |
| Vacuum Pressure | `P_vac` | Pa | Vacuum pressure at chuck | Sensor input or setpoint |
| Wafer Mass | `m_wafer` | kg | Mass of the wafer | Configuration (wafer type) |
| Wafer Radius | `r_wafer` | m | Outer radius of wafer | Configuration (wafer type) |

#### Output Variables
| Variable | Symbol | Unit | Description | Usage in TIA Portal |
|----------|--------|------|-------------|---------------------|
| Slip Factor | `slip_factor` | - | Ratio of inertial to friction force (0.0-1.0+) | Alarm trigger if > 1.0 |
| Max Safe Acceleration | `alpha_max` | rad/s² | Maximum acceleration before slip | Motion profile limit |

#### Parameters (Constants)
| Parameter | Symbol | Value | Unit | Description |
|-----------|--------|-------|------|-------------|
| Coefficient of Friction | μ | 0.6 | - | Rubber/Silicon static friction |
| Chuck Contact Area | A_chuck | Variable | m² | Depends on wafer size |

#### Physics Equations

**1. Friction Force (Holding Force):**
```
F_friction = μ × (P_vac × A_chuck)
```

**2. Inertial Force (Acceleration Force):**
```
F_inertial = m_wafer × r_wafer × α
```
Where:
- For rotational motion: Torque = I × α
- Simplified: Tangential force at edge = m × r × α

**3. Slip Condition:**
```
slip_factor = F_inertial / F_friction

If slip_factor > 1.0:
    Wafer will slip (alarm condition)
```

**4. Maximum Safe Acceleration:**
```
alpha_max = (μ × P_vac × A_chuck) / (m_wafer × r_wafer)
```

### 2.3 Wafer Specifications (from TIA Portal)

Based on `EM_Positioning.scl` wafer types:

| Type | Diameter | Radius | Mass | Contact Area |
|------|----------|--------|------|--------------|
| 1 (300mm) | 0.300 m | 0.150 m | 0.125 kg | 0.0707 m² |
| 2 (200mm) | 0.200 m | 0.100 m | 0.056 kg | 0.0314 m² |
| 3 (150mm) | 0.150 m | 0.075 m | 0.031 kg | 0.0177 m² |

*Note: Mass values are typical for 0.775mm thick silicon wafers*

---

## 3. FMU IMPLEMENTATION OPTIONS

### Option 1: Python with PyFMI/FMPy (Recommended for Beginners)
**Pros:**
- Easy to develop and test
- Good Python library support
- Faster development cycle

**Cons:**
- Requires Python runtime in deployment
- Slightly larger FMU file size

**Tools:**
- `pythonfmu` library for FMU generation
- `fmpy` for testing

### Option 2: C/C# with FMU SDK
**Pros:**
- Native performance
- No runtime dependencies
- Industry standard

**Cons:**
- More complex development
- Requires C/C++ knowledge
- Manual memory management

**Recommendation:** Start with **Python (pythonfmu)** for rapid development, then optionally port to C if performance is critical.

---

## 4. PYTHON FMU IMPLEMENTATION (STEP-BY-STEP)

### 4.1 Environment Setup

#### Step 1: Install Python and Required Libraries
```powershell
# Install Python 3.9+ (if not already installed)
# Download from: https://www.python.org/downloads/

# Create virtual environment
python -m venv fmu_env
.\fmu_env\Scripts\Activate.ps1

# Install required packages
pip install pythonfmu
pip install fmpy
pip install numpy
```

### 4.2 Model Implementation

#### Step 2: Create Python Model File

Create file: `wafer_slip_model.py`

```python
"""
Wafer Slip Dynamics FMU Model
Physics-based simulation of wafer slippage on vacuum chuck
FMI 2.0 Co-Simulation
"""

from pythonfmu import Fmi2Causality, Fmi2Variability, Fmi2Slave
import math

class WaferSlipDynamics(Fmi2Slave):
    """
    FMU Model for Wafer Slip Physics
    
    Calculates slip factor based on:
    - Angular acceleration of spindle
    - Vacuum pressure
    - Wafer physical properties
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # ==================== INPUT VARIABLES ====================
        # From TIA Portal / Simulation
        self.angular_acceleration = 0.0  # rad/s² - Spindle acceleration
        self.vacuum_pressure = 0.0       # Pa - Vacuum pressure (absolute)
        self.wafer_type = 1              # Integer: 1=300mm, 2=200mm, 3=150mm
        
        # ==================== OUTPUT VARIABLES ====================
        self.slip_factor = 0.0           # Dimensionless (0.0-1.0+)
        self.max_safe_acceleration = 0.0 # rad/s² - Maximum safe value
        self.is_slipping = False         # Boolean alarm signal
        
        # ==================== PARAMETERS (CONSTANTS) ====================
        self.mu_friction = 0.6           # Coefficient of friction (rubber/silicon)
        self.safety_margin = 0.85        # Safety factor (trigger at 85% of limit)
        
        # ==================== INTERNAL STATE ====================
        self.wafer_mass = 0.125          # kg
        self.wafer_radius = 0.150        # m
        self.chuck_area = 0.0707         # m²
        
        # Initialize based on default wafer type
        self._update_wafer_properties()
        
        # Register variables for FMU interface
        self.register_variable("angular_acceleration", 
                               causality=Fmi2Causality.input,
                               variability=Fmi2Variability.continuous)
        
        self.register_variable("vacuum_pressure", 
                               causality=Fmi2Causality.input,
                               variability=Fmi2Variability.continuous)
        
        self.register_variable("wafer_type", 
                               causality=Fmi2Causality.input,
                               variability=Fmi2Variability.discrete)
        
        self.register_variable("slip_factor", 
                               causality=Fmi2Causality.output,
                               variability=Fmi2Variability.continuous)
        
        self.register_variable("max_safe_acceleration", 
                               causality=Fmi2Causality.output,
                               variability=Fmi2Variability.continuous)
        
        self.register_variable("is_slipping", 
                               causality=Fmi2Causality.output,
                               variability=Fmi2Variability.discrete)
        
        self.register_variable("mu_friction", 
                               causality=Fmi2Causality.parameter,
                               variability=Fmi2Variability.fixed)
        
        self.register_variable("safety_margin", 
                               causality=Fmi2Causality.parameter,
                               variability=Fmi2Variability.fixed)
    
    def _update_wafer_properties(self):
        """Update wafer physical properties based on wafer type"""
        if self.wafer_type == 1:  # 300mm wafer
            self.wafer_mass = 0.125      # kg
            self.wafer_radius = 0.150    # m
            self.chuck_area = math.pi * (0.150 ** 2)  # Full circle
        elif self.wafer_type == 2:  # 200mm wafer
            self.wafer_mass = 0.056
            self.wafer_radius = 0.100
            self.chuck_area = math.pi * (0.100 ** 2)
        elif self.wafer_type == 3:  # 150mm wafer
            self.wafer_mass = 0.031
            self.wafer_radius = 0.075
            self.chuck_area = math.pi * (0.075 ** 2)
        else:
            # Default to 300mm
            self.wafer_mass = 0.125
            self.wafer_radius = 0.150
            self.chuck_area = 0.0707
    
    def do_step(self, current_time, step_size):
        """
        Perform one simulation step (FMI Co-Simulation)
        
        Args:
            current_time: Current simulation time [s]
            step_size: Time step size [s]
            
        Returns:
            True if step successful
        """
        # Update wafer properties if type changed
        self._update_wafer_properties()
        
        # Calculate friction force (holding force)
        # F_friction = μ × (P_vac × A_chuck)
        # Note: vacuum_pressure should be gauge pressure (negative)
        # Convert to absolute pressure difference
        pressure_diff = abs(self.vacuum_pressure)
        friction_force = self.mu_friction * (pressure_diff * self.chuck_area)
        
        # Calculate inertial force (tangential force at wafer edge)
        # F_inertial = m × r × α
        inertial_force = self.wafer_mass * self.wafer_radius * abs(self.angular_acceleration)
        
        # Calculate slip factor
        if friction_force > 0.001:  # Avoid division by zero
            self.slip_factor = inertial_force / friction_force
        else:
            self.slip_factor = 999.0  # No vacuum = immediate slip
        
        # Calculate maximum safe acceleration
        if self.wafer_mass > 0 and self.wafer_radius > 0:
            self.max_safe_acceleration = friction_force / (self.wafer_mass * self.wafer_radius)
        else:
            self.max_safe_acceleration = 0.0
        
        # Determine if slipping (with safety margin)
        self.is_slipping = (self.slip_factor > self.safety_margin)
        
        return True
    
    def setup_experiment(self, start_time):
        """Initialize experiment"""
        # Reset to safe initial state
        self.slip_factor = 0.0
        self.is_slipping = False
        return True
    
    def enter_initialization_mode(self):
        """Enter initialization mode"""
        return True
    
    def exit_initialization_mode(self):
        """Exit initialization mode"""
        return True
    
    def terminate(self):
        """Terminate simulation"""
        return True
    
    def reset(self):
        """Reset simulation"""
        self.slip_factor = 0.0
        self.is_slipping = False
        return True
```

### 4.3 Building the FMU

#### Step 3: Create Build Script

Create file: `build_fmu.py`

```python
"""
FMU Build Script
Compiles the Python model into an FMU archive
"""

from pythonfmu.builder import FmuBuilder

if __name__ == "__main__":
    # Create FMU builder
    builder = FmuBuilder.build_FMU(
        script_file="wafer_slip_model.py",
        dest=".",  # Output directory
        project_files=[],  # Additional files to include
        documentation_folder=None
    )
    
    print("FMU built successfully!")
    print(f"Output: WaferSlipDynamics.fmu")
```

#### Step 4: Build the FMU
```powershell
# Activate virtual environment (if not already active)
.\fmu_env\Scripts\Activate.ps1

# Run build script
python build_fmu.py
```

This will generate: `WaferSlipDynamics.fmu`

---

## 5. STAND-ALONE FMU TESTING

### 5.1 Test Script with FMPy

Create file: `test_fmu.py`

```python
"""
FMU Stand-alone Test Script
Validates the FMU behavior before integration
"""

from fmpy import *
from fmpy.fmi2 import FMU2Slave
import numpy as np
import matplotlib.pyplot as plt

def test_slip_dynamics():
    """Test the wafer slip FMU with various scenarios"""
    
    fmu_filename = 'WaferSlipDynamics.fmu'
    
    # Extract FMU
    unzipdir = extract(fmu_filename)
    
    # Read model description
    model_description = read_model_description(fmu_filename)
    
    print("=== FMU Model Information ===")
    print(f"Model Name: {model_description.modelName}")
    print(f"FMI Version: {model_description.fmiVersion}")
    print(f"Number of Variables: {len(model_description.modelVariables)}")
    print()
    
    # Instantiate FMU
    fmu = FMU2Slave(guid=model_description.guid,
                    unzipDirectory=unzipdir,
                    modelIdentifier=model_description.coSimulation.modelIdentifier,
                    instanceName='test_instance')
    
    # Initialize
    fmu.instantiate()
    fmu.setupExperiment(startTime=0.0)
    fmu.enterInitializationMode()
    fmu.exitInitializationMode()
    
    print("=== Test Scenario 1: Safe Operation (300mm wafer) ===")
    # Set inputs
    fmu.setInteger([fmu.getVariableByName('wafer_type').valueReference], [1])  # 300mm
    fmu.setReal([fmu.getVariableByName('vacuum_pressure').valueReference], [53000.0])  # 53 kPa
    fmu.setReal([fmu.getVariableByName('angular_acceleration').valueReference], [5.0])  # 5 rad/s²
    
    # Execute step
    fmu.doStep(currentCommunicationPoint=0.0, communicationStepSize=0.1)
    
    # Read outputs
    slip_vr = fmu.getVariableByName('slip_factor').valueReference
    max_acc_vr = fmu.getVariableByName('max_safe_acceleration').valueReference
    slipping_vr = fmu.getVariableByName('is_slipping').valueReference
    
    slip = fmu.getReal([slip_vr])[0]
    max_acc = fmu.getReal([max_acc_vr])[0]
    is_slip = fmu.getBoolean([slipping_vr])[0]
    
    print(f"Slip Factor: {slip:.3f}")
    print(f"Max Safe Acceleration: {max_acc:.2f} rad/s²")
    print(f"Is Slipping: {is_slip}")
    print()
    
    print("=== Test Scenario 2: Aggressive Acceleration (should slip) ===")
    fmu.setReal([fmu.getVariableByName('angular_acceleration').valueReference], [50.0])  # 50 rad/s²
    fmu.doStep(currentCommunicationPoint=0.1, communicationStepSize=0.1)
    
    slip = fmu.getReal([slip_vr])[0]
    is_slip = fmu.getBoolean([slipping_vr])[0]
    
    print(f"Slip Factor: {slip:.3f}")
    print(f"Is Slipping: {is_slip}")
    print()
    
    print("=== Test Scenario 3: Vacuum Loss (should slip) ===")
    fmu.setReal([fmu.getVariableByName('vacuum_pressure').valueReference], [5000.0])  # Low vacuum
    fmu.setReal([fmu.getVariableByName('angular_acceleration').valueReference], [5.0])
    fmu.doStep(currentCommunicationPoint=0.2, communicationStepSize=0.1)
    
    slip = fmu.getReal([slip_vr])[0]
    is_slip = fmu.getBoolean([slipping_vr])[0]
    
    print(f"Slip Factor: {slip:.3f}")
    print(f"Is Slipping: {is_slip}")
    print()
    
    # Terminate
    fmu.terminate()
    fmu.freeInstance()
    
    print("=== All Tests Complete ===")

def plot_acceleration_sweep():
    """Generate characteristic curve: slip factor vs acceleration"""
    
    fmu_filename = 'WaferSlipDynamics.fmu'
    unzipdir = extract(fmu_filename)
    model_description = read_model_description(fmu_filename)
    
    fmu = FMU2Slave(guid=model_description.guid,
                    unzipDirectory=unzipdir,
                    modelIdentifier=model_description.coSimulation.modelIdentifier,
                    instanceName='sweep_instance')
    
    fmu.instantiate()
    fmu.setupExperiment(startTime=0.0)
    fmu.enterInitializationMode()
    fmu.exitInitializationMode()
    
    # Test parameters
    vacuum_pressure = 53000.0  # Pa (53 kPa - typical value)
    wafer_type = 1  # 300mm
    
    # Set fixed inputs
    fmu.setInteger([fmu.getVariableByName('wafer_type').valueReference], [wafer_type])
    fmu.setReal([fmu.getVariableByName('vacuum_pressure').valueReference], [vacuum_pressure])
    
    # Sweep acceleration
    accelerations = np.linspace(0, 50, 100)  # 0 to 50 rad/s²
    slip_factors = []
    
    acc_vr = fmu.getVariableByName('angular_acceleration').valueReference
    slip_vr = fmu.getVariableByName('slip_factor').valueReference
    
    time = 0.0
    for acc in accelerations:
        fmu.setReal([acc_vr], [float(acc)])
        fmu.doStep(currentCommunicationPoint=time, communicationStepSize=0.01)
        slip = fmu.getReal([slip_vr])[0]
        slip_factors.append(slip)
        time += 0.01
    
    fmu.terminate()
    fmu.freeInstance()
    
    # Plot results
    plt.figure(figsize=(10, 6))
    plt.plot(accelerations, slip_factors, 'b-', linewidth=2, label='Slip Factor')
    plt.axhline(y=1.0, color='r', linestyle='--', linewidth=2, label='Slip Threshold')
    plt.axhline(y=0.85, color='orange', linestyle='--', linewidth=2, label='Safety Margin')
    plt.xlabel('Angular Acceleration (rad/s²)', fontsize=12)
    plt.ylabel('Slip Factor', fontsize=12)
    plt.title(f'Wafer Slip Characteristics\n(300mm wafer, {vacuum_pressure/1000:.0f} kPa vacuum)', fontsize=14)
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=10)
    plt.tight_layout()
    plt.savefig('slip_characteristic.png', dpi=300)
    print("Plot saved: slip_characteristic.png")
    plt.show()

if __name__ == "__main__":
    # Run basic tests
    test_slip_dynamics()
    
    # Generate characteristic plot
    plot_acceleration_sweep()
```

#### Step 5: Run Tests
```powershell
# Install matplotlib for plotting (if not installed)
pip install matplotlib

# Run test script
python test_fmu.py
```

**Expected Results:**
- Scenario 1: slip_factor < 0.85 (safe)
- Scenario 2: slip_factor > 1.0 (slipping)
- Scenario 3: slip_factor > 1.0 (vacuum loss)
- Plot: Shows characteristic curve

---

## 6. FMU INTEGRATION WITH SIEMENS NX MCD

### 6.1 Integration Pathway

**Option A: Direct FMU Import (if supported)**
1. In Siemens NX MCD, navigate to FMU import function
2. Select `WaferSlipDynamics.fmu`
3. Map FMU inputs to simulation signals
4. Map FMU outputs to alarm/display systems

**Option B: PLCSim Advanced Integration**
1. Use TIA Portal PLCSim Advanced
2. Create OPC UA server for FMU
3. Link FMU outputs to PLC tags
4. Trigger alarms in TIA Portal when `is_slipping = TRUE`

### 6.2 Signal Mapping Table

| FMU Input | TIA Portal Source | Connection Method |
|-----------|-------------------|-------------------|
| `angular_acceleration` | Calculated from `EM_Spindle.Output.q_rlVelocity` (derivative) | OPC UA / Signal mapping |
| `vacuum_pressure` | `I_Chuck_Vacuum_Pressure` (sensor) | Direct tag read |
| `wafer_type` | `UN_WaferAligner.Input.i_diWaferType` | Configuration tag |

| FMU Output | TIA Portal Destination | Action |
|------------|------------------------|--------|
| `slip_factor` | HMI display tag | Monitoring |
| `max_safe_acceleration` | Motion profile limiter | Velocity override |
| `is_slipping` | Alarm tag | Trigger "Position Error" alarm |

### 6.3 Integration Code Example (TIA Portal SCL)

Add to `UN_WaferAligner.scl` or create new FB:

```scl
// =================================================================
// FMU Interface Block (Pseudo-code for integration)
// =================================================================

// Local variables
#LVrlPreviousVelocity : REAL; // For acceleration calculation
#LVrlCurrentVelocity : REAL;
#LVrlDeltaTime : REAL := 0.01; // 10ms cycle time
#LVrlAcceleration : REAL;

// Calculate acceleration from velocity change
#LVrlCurrentVelocity := #ioUnit.emSpindle.Output.q_rlVelocity;
#LVrlAcceleration := (#LVrlCurrentVelocity - #LVrlPreviousVelocity) / #LVrlDeltaTime;
#LVrlPreviousVelocity := #LVrlCurrentVelocity;

// Write to FMU inputs (via OPC UA or similar)
"FMU_Input_Acceleration" := #LVrlAcceleration;
"FMU_Input_VacuumPressure" := "I_Chuck_Vacuum_Pressure";
"FMU_Input_WaferType" := #ioUnit.Input.i_diWaferType;

// Read from FMU outputs
#ioUnit.HMI.hmi_rlSlipFactor := "FMU_Output_SlipFactor";
#ioUnit.HMI.hmi_blSlipAlarm := "FMU_Output_IsSlipping";

// Trigger alarm if slipping detected
IF "FMU_Output_IsSlipping" THEN
    // Set alarm bit
    #ioUnit.Status.s_blSlipAlarm := TRUE;
    // Optional: Emergency stop
    #ioUnit.Input.i_blStop := TRUE;
END_IF;
```

---

## 7. FMU PORTABILITY DEMONSTRATION

### 7.1 Test in Alternative FMI-Compliant Tool

To satisfy the mandatory requirement in Section 4.3 of the assignment document, demonstrate FMU portability by testing in at least one external tool.

#### Recommended Tools:
1. **FMPy** (already shown above) ✓
2. **OpenModelica** (free, open-source)
3. **Dymola** (commercial, trial available)
4. **MATLAB/Simulink** (with FMU Import block)

#### Example: OpenModelica Integration

**Step 1: Install OpenModelica**
- Download from: https://openmodelica.org/

**Step 2: Import FMU in OMEdit**
```modelica
model WaferAlignerTest
  FMI2.FMU fmu(fmuFile="WaferSlipDynamics.fmu");
  Modelica.Blocks.Sources.Ramp acceleration(height=50, duration=10);
  Modelica.Blocks.Sources.Constant vacuum(k=53000);
  
equation
  connect(acceleration.y, fmu.angular_acceleration);
  connect(vacuum.y, fmu.vacuum_pressure);
  
end WaferAlignerTest;
```

**Step 3: Simulate and Document**
- Run simulation
- Capture screenshot of results
- Include in report as proof of portability

### 7.2 Evidence Checklist
For the report, include:
- [ ] Screenshot of FMU loaded in external tool
- [ ] Simulation results plot
- [ ] Statement: "The FMU was successfully tested in [Tool Name], demonstrating FMI 2.0 compliance and portability"

---

## 8. DOCUMENTATION FOR REPORT

### 8.1 Section 7: FMU Background, Implementation, Tests, and Integration

Use this structure in your individual report:

#### 7.1 Technical Background of FMU/FMI
- Definition of FMU and FMI standard
- Model Exchange vs Co-Simulation (with comparison table)
- FMU structure (XML + binaries + resources)
- **Reference:** FMI 2.0 Standard Specification

#### 7.2 FMU Implementation
- **Model Description:** Wafer slip dynamics physics
- **Equations:** Include all equations from Section 2.2
- **Tool Selection:** Python with `pythonfmu` (justify choice)
- **Code Structure:** Class diagram showing variables and methods
- **Include:** Snippets of `wafer_slip_model.py` (key sections)

#### 7.3 Stand-alone Testing
- **Test Cases:** 
  - Safe operation (low acceleration)
  - Slip condition (high acceleration)
  - Vacuum loss scenario
- **Results:** Table with inputs, expected outputs, actual outputs
- **Characteristic Plot:** Include `slip_characteristic.png`
- **Pass/Fail Criteria:** All tests pass (slip detection correct)

#### 7.4 FMU Integration & Portability
- **Integration Pathway:** Describe connection to NX MCD/TIA Portal
- **Signal Mapping:** Table from Section 6.2
- **Portability Demonstration:** 
  - Tool used (e.g., FMPy, OpenModelica)
  - Evidence: Screenshot + results plot
  - Statement of successful export

#### 7.5 Validation & Lessons Learned
- Compare FMU predictions with expected physics
- Discuss limitations (e.g., static friction model vs. dynamic)
- Future improvements (e.g., more sophisticated friction model)

---

## 9. TROUBLESHOOTING GUIDE

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| `pythonfmu` install fails | Missing C++ compiler | Install Visual Studio Build Tools |
| FMU build error | Python version mismatch | Use Python 3.9-3.11 |
| FMU won't load in tool | FMI version incompatibility | Verify tool supports FMI 2.0 CS |
| Division by zero error | Zero vacuum pressure | Add check in code (see `friction_force > 0.001`) |
| Slip factor always > 1 | Pressure units wrong | Ensure vacuum_pressure in Pascals (Pa), not kPa |

### Debugging Tips
1. **Test Python model standalone** before building FMU
2. **Use `fmpy.dump()` to inspect FMU contents**
3. **Check modelDescription.xml** for correct variable definitions
4. **Validate units** - common source of errors

---

## 10. IMPLEMENTATION CHECKLIST

### Development Phase
- [ ] Install Python environment and libraries
- [ ] Implement `wafer_slip_model.py`
- [ ] Create `build_fmu.py` script
- [ ] Build FMU successfully
- [ ] Verify FMU structure (unzip and check)

### Testing Phase
- [ ] Write test script `test_fmu.py`
- [ ] Execute all test scenarios
- [ ] Generate characteristic plot
- [ ] Document test results in table

### Integration Phase
- [ ] Identify integration pathway (NX/PLCSim/OPC UA)
- [ ] Create signal mapping table
- [ ] Test FMU in external tool (portability)
- [ ] Capture evidence (screenshots)

### Documentation Phase
- [ ] Write Section 7.1 (Background)
- [ ] Write Section 7.2 (Implementation)
- [ ] Write Section 7.3 (Testing)
- [ ] Write Section 7.4 (Integration)
- [ ] Include all diagrams and code snippets
- [ ] Review against assignment requirements

---

## 11. REFERENCES

1. **FMI Standard:** Functional Mock-up Interface Specification 2.0  
   https://fmi-standard.org/

2. **PythonFMU Documentation:**  
   https://github.com/NTNU-IHB/PythonFMU

3. **FMPy Documentation:**  
   https://github.com/CATIA-Systems/FMPy

4. **Friction Physics Reference:**  
   Budynas & Nisbett, "Shigley's Mechanical Engineering Design"

5. **Wafer Handling Standards:**  
   SEMI M1 Specification for Wafer Dimensions

---

## APPENDIX A: COMPLETE FILE LIST

Files you need to create:

1. **wafer_slip_model.py** - Main FMU model implementation
2. **build_fmu.py** - FMU build script
3. **test_fmu.py** - Stand-alone test script
4. **requirements.txt** - Python dependencies

Create `requirements.txt`:
```
pythonfmu>=0.6.3
fmpy>=0.3.16
numpy>=1.21.0
matplotlib>=3.5.0
```

---

## APPENDIX B: ADVANCED FEATURES (OPTIONAL)

If time permits, consider these enhancements:

### B.1 Dynamic Friction Model
Currently uses static friction. Add:
- Velocity-dependent friction coefficient
- Stiction vs kinetic friction transition

### B.2 Wafer Deflection
Add structural dynamics:
- Wafer bending under acceleration
- Stress distribution on chuck

### B.3 Multi-Zone Vacuum
Model chuck with multiple vacuum zones:
- Non-uniform pressure distribution
- Zone-specific leak detection

### B.4 Real-Time Monitoring
Add data logging:
- Export time-series data to CSV
- Generate real-time plots during simulation

---

## CONCLUSION

This guide provides a complete pathway from FMU concept to implementation and testing. The Python-based approach balances ease of development with professional standards compliance.

**Key Success Factors:**
1. **Understand the physics** before coding
2. **Test incrementally** (Python → FMU → Integration)
3. **Document thoroughly** with evidence
4. **Verify portability** with external tool

The FMU you create will demonstrate:
- ✓ Technical understanding of FMI standard
- ✓ Ability to model complex physics
- ✓ Software engineering skills (Python/C#)
- ✓ Integration capability with Digital Twin
- ✓ Validation through systematic testing

**Good luck with your implementation!**
