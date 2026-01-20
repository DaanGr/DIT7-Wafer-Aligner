model WaferSlipDynamics
  // ==================== INPUTS ====================
  parameter Real mu_friction = 0.6 "Coefficient of friction";
  parameter Real safety_margin = 0.85 "Safety factor trigger";
  parameter Real nominal_vacuum_pressure = 53000.0 "Pa";
  
  input Real angular_acceleration "rad/s2";
  input Boolean vacuum_active;
  input Integer wafer_type "1=300mm, 2=200mm, 3=150mm";

  // ==================== OUTPUTS ====================
  output Real slip_factor;
  output Real max_safe_acceleration "rad/s2";
  output Boolean is_slipping;

  // ==================== INTERNAL VARIABLES ====================
  protected
    Real wafer_mass;
    Real wafer_radius;
    Real chuck_area;
    Real pressure;
    Real friction_force;
    Real inertial_force;
    constant Real pi = 3.14159265358979;

equation
  // 1. Define Wafer Geometry based on type
  chuck_area = pi * (0.030 ^ 2);
  
  wafer_radius = if wafer_type == 1 then 0.150 
                 else if wafer_type == 2 then 0.100 
                 else 0.075;
                 
  wafer_mass = if wafer_type == 1 then 2330 * (pi * 0.150^2 * 0.0005)
               else if wafer_type == 2 then 2330 * (pi * 0.100^2 * 0.0005)
               else 2330 * (pi * 0.075^2 * 0.0005);

  // 2. Physics Calculations
  pressure = if vacuum_active then nominal_vacuum_pressure else 0.0;
  friction_force = mu_friction * (pressure * chuck_area);
  inertial_force = wafer_mass * wafer_radius * abs(angular_acceleration);

  // 3. Output Logic
  slip_factor = if friction_force > 0.001 then (inertial_force / friction_force) else 999.0;
  max_safe_acceleration = if (wafer_mass * wafer_radius) > 0 then (friction_force / (wafer_mass * wafer_radius)) else 0.0;
  is_slipping = slip_factor > safety_margin;

end WaferSlipDynamics;
