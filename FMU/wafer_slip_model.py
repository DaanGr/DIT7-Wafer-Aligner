"""
Wafer Slip Dynamics FMU Model
Physics-based simulation of wafer slippage on vacuum chuck
FMI 2.0 Co-Simulation
"""

from pythonfmu import Fmi2Causality, Fmi2Variability, Fmi2Slave, Real, Integer, Boolean
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
        self.register_variable(Real("angular_acceleration", 
                               causality=Fmi2Causality.input,
                               variability=Fmi2Variability.continuous))
        
        self.register_variable(Real("vacuum_pressure", 
                               causality=Fmi2Causality.input,
                               variability=Fmi2Variability.continuous))
        
        self.register_variable(Integer("wafer_type", 
                               causality=Fmi2Causality.input,
                               variability=Fmi2Variability.discrete))
        
        self.register_variable(Real("slip_factor", 
                               causality=Fmi2Causality.output,
                               variability=Fmi2Variability.continuous))
        
        self.register_variable(Real("max_safe_acceleration", 
                               causality=Fmi2Causality.output,
                               variability=Fmi2Variability.continuous))
        
        self.register_variable(Boolean("is_slipping", 
                               causality=Fmi2Causality.output,
                               variability=Fmi2Variability.discrete))
        
        self.register_variable(Real("mu_friction", 
                               causality=Fmi2Causality.parameter,
                               variability=Fmi2Variability.fixed))
        
        self.register_variable(Real("safety_margin", 
                               causality=Fmi2Causality.parameter,
                               variability=Fmi2Variability.fixed))
    
    def _update_wafer_properties(self):
        """Update wafer physical properties based on wafer type"""
        # Chuck has a fixed diameter of 60mm (0.030m radius)
        chuck_radius = 0.030
        self.chuck_area = math.pi * (chuck_radius ** 2)
        wafer_density = 2330 # kg/m³ for silicon
        wafer_thickness = 0.5 # mm
        
        if self.wafer_type == 1:  # 300mm wafer
            self.wafer_mass = wafer_density * (math.pi * (0.150 ** 2) * wafer_thickness * 1e-3)  # kg
            self.wafer_radius = 0.150    # m
        elif self.wafer_type == 2:  # 200mm wafer
            self.wafer_mass = wafer_density * (math.pi * (0.100 ** 2) * wafer_thickness * 1e-3)  # kg
            self.wafer_radius = 0.100
        elif self.wafer_type == 3:  # 150mm wafer
            self.wafer_mass = wafer_density * (math.pi * (0.075 ** 2) * wafer_thickness * 1e-3)  # kg  
            self.wafer_radius = 0.075
        else:
            # Default to 300mm
            self.wafer_mass = wafer_density * (math.pi * (0.150 ** 2) * wafer_thickness * 1e-3)  # kg
            self.wafer_radius = 0.150
    
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
    
    def setup_experiment(self, start_time, stop_time=None, tolerance=None):
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