"""
FMU Stand-alone Test Script
Validates the FMU behavior before integration
"""

from fmpy import extract, read_model_description
from fmpy.fmi2 import FMU2Slave
import numpy as np
import matplotlib.pyplot as plt

def test_slip_dynamics():
    """Test the wafer slip FMU with various scenarios and plot results"""
    
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    fmu_filename = os.path.join(script_dir, '..', 'WaferSlipDynamics.fmu')
    
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
    
    results = []
    
    print("=== Test Scenario 1: Safe Operation (200mm wafer) ===")
    # Set inputs
    fmu.setInteger([vrs['wafer_type']], [2])  # 200mm
    fmu.setBoolean([vrs['vacuum_active']], [True])  # Vacuum ON
    fmu.setReal([vrs['angular_acceleration']], [5.0])  # 5 rad/s²
    
    # Execute step
    fmu.doStep(currentCommunicationPoint=0.0, communicationStepSize=0.1)
    
    # Read outputs
    slip1 = fmu.getReal([vrs['slip_factor']])[0]
    max_acc = fmu.getReal([vrs['max_safe_acceleration']])[0]
    is_slip1 = fmu.getBoolean([vrs['is_slipping']])[0]
    results.append({'name': 'Safe Op', 'slip': slip1, 'slipping': is_slip1})
    
    print(f"Slip Factor: {slip1:.6f}")
    print(f"Max Safe Acceleration: {max_acc:.2f} rad/s²")
    print(f"Is Slipping: {is_slip1}")
    print()
    
    print("=== Test Scenario 2: Aggressive Acceleration (should slip) ===")
    # With full vacuum, we need huge acceleration to slip
    # Let's try 150,000 rad/s² (using default nominal pressure of 53kPa)
    fmu.setReal([vrs['angular_acceleration']], [150000.0])  
    fmu.doStep(currentCommunicationPoint=0.1, communicationStepSize=0.1)
    
    slip2 = fmu.getReal([vrs['slip_factor']])[0]
    is_slip2 = fmu.getBoolean([vrs['is_slipping']])[0]
    results.append({'name': 'High Accel', 'slip': slip2, 'slipping': is_slip2})
    
    print(f"Slip Factor: {slip2:.6f}")
    print(f"Is Slipping: {is_slip2}")
    print()
    
    print("=== Test Scenario 3: Vacuum Loss (should slip) ===")
    fmu.setBoolean([vrs['vacuum_active']], [False])  # Vacuum OFF (0 Pa)
    fmu.setReal([vrs['angular_acceleration']], [5.0])
    fmu.doStep(currentCommunicationPoint=0.2, communicationStepSize=0.1)
    
    slip3 = fmu.getReal([vrs['slip_factor']])[0]
    is_slip3 = fmu.getBoolean([vrs['is_slipping']])[0]
    results.append({'name': 'Low Vacuum', 'slip': slip3, 'slipping': is_slip3})
    
    print(f"Slip Factor: {slip3:.6f}")
    print(f"Is Slipping: {is_slip3}")
    print()
    
    # Terminate
    fmu.terminate()
    fmu.freeInstance()
    
    # Plot results
    plt.figure(figsize=(10, 6))
    names = [r['name'] for r in results]
    values = [r['slip'] for r in results]
    colors = ['r' if r['slipping'] else 'g' for r in results]
    
    bars = plt.bar(names, values, color=colors)
    plt.axhline(y=1.0, color='r', linestyle='--', label='Slip Threshold')
    plt.axhline(y=0.85, color='orange', linestyle='--', label='Safety Margin')
    plt.ylabel('Slip Factor')
    plt.title('Test Scenarios Summary')
    plt.legend()
    
    # Add value labels
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height,
                 f'{height:.2f}',
                 ha='center', va='bottom')

    plt.savefig(os.path.join(script_dir, 'test_scenarios_results.png'), dpi=300)
    print("Plot saved: test_scenarios_results.png")
    
    print("=== All Tests Complete ===")

def plot_acceleration_sweep():
    """Generate characteristic curve: slip factor vs acceleration"""
    
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    fmu_filename = os.path.join(script_dir, '..', 'WaferSlipDynamics.fmu')

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
    wafer_type = 2  # 200mm
    
    # Set fixed inputs
    fmu.setInteger([vrs['wafer_type']], [wafer_type])
    fmu.setBoolean([vrs['vacuum_active']], [True])
    fmu.setReal([vrs['nominal_vacuum_pressure']], [vacuum_pressure])
    
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
    plt.title(f'Wafer Slip Characteristics\n(200mm wafer, {vacuum_pressure/1000:.0f} kPa vacuum)', fontsize=14)
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=10)
    plt.tight_layout()
    plt.savefig(os.path.join(script_dir, 'slip_characteristic.png'), dpi=300)
    print("Plot saved: slip_characteristic.png")
    # plt.show() # Disabled for headless environment

def plot_vacuum_sweep():
    """Generate characteristic curve: slip factor vs vacuum pressure"""
    
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    fmu_filename = os.path.join(script_dir, '..', 'WaferSlipDynamics.fmu')

    unzipdir = extract(fmu_filename)
    model_description = read_model_description(fmu_filename)
    
    # Map variable names to value references
    vrs = {v.name: v.valueReference for v in model_description.modelVariables}
    
    fmu = FMU2Slave(guid=model_description.guid,
                    unzipDirectory=unzipdir,
                    modelIdentifier=model_description.coSimulation.modelIdentifier,
                    instanceName='vacuum_sweep_instance')
    
    fmu.instantiate()
    fmu.setupExperiment(startTime=0.0)
    fmu.enterInitializationMode()
    fmu.exitInitializationMode()
    
    # Test parameters
    acceleration = 5.0  # rad/s^2 - From Scenario 1/3
    wafer_type = 2  # 200mm
    
    # Set fixed inputs
    fmu.setInteger([vrs['wafer_type']], [wafer_type])
    fmu.setReal([vrs['angular_acceleration']], [acceleration])
    fmu.setBoolean([vrs['vacuum_active']], [True])
    
    # Sweep vacuum pressure (PARAMETER)
    pressures = np.linspace(0, 1000, 100)  # 0 to 10 kPa
    slip_factors = []
    
    vac_vr = vrs['nominal_vacuum_pressure']
    slip_vr = vrs['slip_factor']
    
    time = 0.0
    for press in pressures:
        fmu.setReal([vac_vr], [float(press)])
        fmu.doStep(currentCommunicationPoint=time, communicationStepSize=0.01)
        slip = fmu.getReal([slip_vr])[0]
        slip_factors.append(slip)
        time += 0.01
    
    fmu.terminate()
    fmu.freeInstance()
    
    # Plot results
    plt.figure(figsize=(10, 6))
    plt.plot(pressures/1000, slip_factors, 'b-', linewidth=2, label='Slip Factor')
    plt.axhline(y=1.0, color='r', linestyle='--', linewidth=2, label='Slip Threshold')
    plt.axhline(y=0.85, color='orange', linestyle='--', linewidth=2, label='Safety Margin')
    plt.xlabel('Vacuum Pressure (kPa)', fontsize=12)
    plt.ylabel('Slip Factor', fontsize=12)
    plt.title(f'Wafer Slip vs Vacuum Pressure\n(200mm wafer, {acceleration} rad/s²)', fontsize=14)
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=10)
    plt.tight_layout()
    plt.savefig(os.path.join(script_dir, 'vacuum_characteristic.png'), dpi=300)
    print("Plot saved: vacuum_characteristic.png")

def plot_3d_combined_sweep():
    """Generate 2D Contour plot: Slip Factor vs (Acceleration, Vacuum)"""
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    fmu_filename = os.path.join(script_dir, '..', 'WaferSlipDynamics.fmu')
    
    unzipdir = extract(fmu_filename)
    model_description = read_model_description(fmu_filename)
    vrs = {v.name: v.valueReference for v in model_description.modelVariables}
    
    fmu = FMU2Slave(guid=model_description.guid,
                    unzipDirectory=unzipdir,
                    modelIdentifier=model_description.coSimulation.modelIdentifier,
                    instanceName='contour_instance')
    
    fmu.instantiate()
    fmu.setupExperiment(startTime=0.0)
    fmu.enterInitializationMode()
    fmu.exitInitializationMode()
    
    # Ranges
    # Acceleration: 0 to 100 rad/s^2 
    acc_range = np.linspace(0, 200, 50)
    # Vacuum: 0 kPa to 60 kPa
    vac_range = np.linspace(0, 5000, 50)
    
    X, Y = np.meshgrid(acc_range, vac_range)
    Z = np.zeros_like(X)
    
    acc_vr = vrs['angular_acceleration']
    vac_vr = vrs['nominal_vacuum_pressure']
    vac_active_vr = vrs['vacuum_active']
    slip_vr = vrs['slip_factor']
    wafer_type_vr = vrs['wafer_type']
    
    # Set wafer type to 200mm
    fmu.setInteger([wafer_type_vr], [2])
    fmu.setBoolean([vac_active_vr], [True])
    
    time = 0.0
    for i in range(len(vac_range)):
        for j in range(len(acc_range)):
            vac = float(vac_range[i])
            acc = float(acc_range[j])
            
            fmu.setReal([vac_vr, acc_vr], [vac, acc])
            fmu.doStep(currentCommunicationPoint=time, communicationStepSize=0.01)
            
            slip = fmu.getReal([slip_vr])[0]
            Z[i, j] = slip
            time += 0.01
            
    fmu.terminate()
    fmu.freeInstance()
    
    # Plotting
    plt.figure(figsize=(10, 8))
    
    # Plot contour
    # Use logarithmic scaling for easier visualization of low slip factors
    # But include 0 explicitly? Log of 0 is -inf. 
    # Let's stick to linear but focusing on the threshold
    
    levels = np.linspace(0, 2.0, 20) # Focus on 0 to 2
    cp = plt.contourf(X, Y/1000, Z, levels=levels, cmap='RdYlGn_r', extend='max')
    cbar = plt.colorbar(cp)
    cbar.set_label('Slip Factor')
    
    # Add a specific line for the threshold
    cs = plt.contour(X, Y/1000, Z, levels=[0.85, 1.0], colors=['orange', 'red'], linewidths=2)
    plt.clabel(cs, inline=True, fontsize=10, fmt={0.85: 'Safety (0.85)', 1.0: 'Slip (1.0)'})
    
    plt.xlabel('Angular Acceleration (rad/s²)')
    plt.ylabel('Vacuum Pressure (kPa)')
    plt.title('Wafer Slip Risk Profile (200mm Wafer)')
    plt.grid(True, alpha=0.3)

    plt.savefig(os.path.join(script_dir, 'slip_risk_contour.png'), dpi=300)
    print("Plot saved: slip_risk_contour.png")

if __name__ == "__main__":
    # Run basic tests
    test_slip_dynamics()
    
    # Generate characteristic plots
    plot_acceleration_sweep()
    plot_vacuum_sweep()
    plot_3d_combined_sweep()

