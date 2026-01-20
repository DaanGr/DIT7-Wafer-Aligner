using System;

namespace FMU.NET
{
    /// <summary>
    /// Wafer Slip Dynamics FMU Model
    /// Physics-based simulation of wafer slippage on vacuum chuck
    /// Compatible with FMI 2.0 Co-Simulation standards
    /// </summary>
    public class WaferSlipDynamics
    {
        // ==================== INPUT VARIABLES ====================
        // From TIA Portal / Simulation
        
        /// <summary>
        /// Angular acceleration of spindle in rad/s²
        /// Value Reference: 1
        /// </summary>
        public double AngularAcceleration { get; set; }

        /// <summary>
        /// Vacuum Active Status (True/False)
        /// Value Reference: 2
        /// </summary>
        public bool VacuumActive { get; set; }

        /// <summary>
        /// Wafer Type: 1=300mm, 2=200mm, 3=150mm
        /// Value Reference: 3
        /// </summary>
        public int WaferType { get; set; }

        // ==================== OUTPUT VARIABLES ====================
        
        /// <summary>
        /// Calculated dimensionless slip factor (0.0 - 1.0+)
        /// Value Reference: 4
        /// </summary>
        public double SlipFactor { get; private set; }

        /// <summary>
        /// Maximum safe angular acceleration in rad/s²
        /// Value Reference: 5
        /// </summary>
        public double MaxSafeAcceleration { get; private set; }

        /// <summary>
        /// Boolean alarm signal. True if slipping.
        /// Value Reference: 6
        /// </summary>
        public bool IsSlipping { get; private set; }

        // ==================== PARAMETERS (CONSTANTS) ====================
        
        /// <summary>
        /// Coefficient of friction (rubber/silicon)
        /// Value Reference: 7
        /// </summary>
        public double MuFriction { get; set; }

        /// <summary>
        /// Safety margin factor (trigger at 85% of limit)
        /// Value Reference: 8
        /// </summary>
        public double SafetyMargin { get; set; }

        /// <summary>
        /// Vacuum pressure in Pa when active
        /// Value Reference: 9
        /// </summary>
        public double NominalVacuumPressure { get; set; }

        // ==================== INTERNAL STATE ====================
        private double _waferMass;
        private double _waferRadius;
        private double _chuckArea;

        /// <summary>
        /// Constructor
        /// Initializes all variables to default safe values to prevent memory violations.
        /// </summary>
        public WaferSlipDynamics()
        {
            // Initialize Inputs
            AngularAcceleration = 0.0;
            VacuumActive = false;
            WaferType = 1; // Default to 300mm

            // Initialize Outputs
            SlipFactor = 0.0;
            MaxSafeAcceleration = 0.0;
            IsSlipping = false;

            // Initialize Parameters
            MuFriction = 0.6;
            SafetyMargin = 0.85;
            NominalVacuumPressure = 53000.0; // 53 kPa

            // Initialize Internal State
            _updateWaferProperties();
        }

        /// <summary>
        /// Update internal physical properties based on the selected WaferType
        /// </summary>
        private void _updateWaferProperties()
        {
            // Chuck has a fixed diameter of 60mm (0.030m radius)
            double chuckRadius = 0.030;
            _chuckArea = Math.PI * Math.Pow(chuckRadius, 2);
            
            double waferDensity = 2330.0; // kg/m³ for silicon
            double waferThickness = 0.5;  // mm

            if (WaferType == 1) // 300mm wafer
            {
                _waferRadius = 0.150;
                _waferMass = waferDensity * (Math.PI * Math.Pow(_waferRadius, 2) * waferThickness * 1e-3);
            }
            else if (WaferType == 2) // 200mm wafer
            {
                _waferRadius = 0.100;
                 _waferMass = waferDensity * (Math.PI * Math.Pow(_waferRadius, 2) * waferThickness * 1e-3);
            }
            else if (WaferType == 3) // 150mm wafer
            {
                _waferRadius = 0.075;
                 _waferMass = waferDensity * (Math.PI * Math.Pow(_waferRadius, 2) * waferThickness * 1e-3);
            }
            else
            {
                // Fallback / Default to 300mm
                _waferRadius = 0.150;
                 _waferMass = waferDensity * (Math.PI * Math.Pow(_waferRadius, 2) * waferThickness * 1e-3);
            }
        }

        /// <summary>
        /// FMI 2.0 Initialize
        /// </summary>
        public void EnterInitializationMode()
        {
            // Reset to safe initial state
            SlipFactor = 0.0;
            IsSlipping = false;
            _updateWaferProperties();
        }

        /// <summary>
        /// FMI 2.0 Exit Initialization
        /// </summary>
        public void ExitInitializationMode()
        {
             // Post-initialization checks could go here
             _updateWaferProperties();
        }
        
        /// <summary>
        /// FMI 2.0 Setup Experiment
        /// </summary>
        public void SetupExperiment(double startTime, double stopTime, double tolerance)
        {
            // Can be used to set time variables if needed
        }

        /// <summary>
        /// Perform one simulation step (FMI Co-Simulation)
        /// Corresponds to fmi2DoStep
        /// </summary>
        /// <param name="currentCommunicationPoint">Current simulation time</param>
        /// <param name="communicationStepSize">Time step size</param>
        public void DoStep(double currentCommunicationPoint, double communicationStepSize)
        {
            // 1. Update properties in case inputs changed
            _updateWaferProperties();

            // 2. Calculate friction force (holding force)
            // F_friction = μ × (P_vac × A_chuck)
            double pressure = VacuumActive ? NominalVacuumPressure : 0.0;
            double frictionForce = MuFriction * (pressure * _chuckArea);

            // 3. Calculate inertial force (tangential force at wafer edge)
            // F_inertial = m × r × α
            double inertialForce = _waferMass * _waferRadius * Math.Abs(AngularAcceleration);

            // 4. Calculate slip factor
            if (frictionForce > 0.001)
            {
                SlipFactor = inertialForce / frictionForce;
            }
            else
            {
                // No vacuum holding force = immediate slip if any movement, or conceptually infinite risk
                SlipFactor = 999.0; 
            }

            // 5. Calculate maximum safe acceleration
            // α_max = F_friction / (m * r)
            if (_waferMass > 0 && _waferRadius > 0)
            {
                MaxSafeAcceleration = frictionForce / (_waferMass * _waferRadius);
            }
            else
            {
                MaxSafeAcceleration = 0.0;
            }

            // 6. Determine if slipping (with safety margin)
            IsSlipping = (SlipFactor > SafetyMargin);
        }
    }
}
