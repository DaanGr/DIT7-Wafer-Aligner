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
    
    # Map variable names to value references
    vrs = {v.name: v.valueReference for v in model_description.modelVariables}
    
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
    fmu.setInteger([vrs['wafer_type']], [1])  # 300mm
    fmu.setReal([vrs['vacuum_pressure']], [53000.0])  # 53 kPa
    fmu.setReal([vrs['angular_acceleration']], [5.0])  # 5 rad/s²
    
    # Execute step
    fmu.doStep(currentCommunicationPoint=0.0, communicationStepSize=0.1)
    
    # Read outputs
    slip = fmu.getReal([vrs['slip_factor']])[0]
    max_acc = fmu.getReal([vrs['max_safe_acceleration']])[0]
    is_slip = fmu.getBoolean([vrs['is_slipping']])[0]
    
    print(f"Slip Factor: {slip:.6f}")
    print(f"Max Safe Acceleration: {max_acc:.2f} rad/s²")
    print(f"Is Slipping: {is_slip}")
    print()
    
    print("=== Test Scenario 2: Aggressive Acceleration (should slip) ===")
    # With full vacuum, we need huge acceleration to slip
    # Let's try 150,000 rad/s²
    fmu.setReal([vrs['angular_acceleration']], [150000.0])  
    fmu.doStep(currentCommunicationPoint=0.1, communicationStepSize=0.1)
    
    slip = fmu.getReal([vrs['slip_factor']])[0]
    is_slip = fmu.getBoolean([vrs['is_slipping']])[0]
    
    print(f"Slip Factor: {slip:.6f}")
    print(f"Is Slipping: {is_slip}")
    print()
    
    print("=== Test Scenario 3: Vacuum Loss (should slip) ===")
    fmu.setReal([vrs['vacuum_pressure']], [10.0])  # Extremely low vacuum (10 Pa)
    fmu.setReal([vrs['angular_acceleration']], [5.0])
    fmu.doStep(currentCommunicationPoint=0.2, communicationStepSize=0.1)
    
    slip = fmu.getReal([vrs['slip_factor']])[0]
    is_slip = fmu.getBoolean([vrs['is_slipping']])[0]
    
    print(f"Slip Factor: {slip:.6f}")
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
    
    # Map variable names to value references
    vrs = {v.name: v.valueReference for v in model_description.modelVariables}
    
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
    fmu.setInteger([vrs['wafer_type']], [wafer_type])
    fmu.setReal([vrs['vacuum_pressure']], [vacuum_pressure])
    
    # Sweep acceleration
    accelerations = np.linspace(0, 50, 100)  # 0 to 50 rad/s²
    slip_factors = []
    
    acc_vr = vrs['angular_acceleration']
    slip_vr = vrs['slip_factor']
    
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
    # plt.show() # Disabled for headless environment

if __name__ == "__main__":
    # Run basic tests
    test_slip_dynamics()
    
    # Generate characteristic plot
    plot_acceleration_sweep()