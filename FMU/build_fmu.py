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