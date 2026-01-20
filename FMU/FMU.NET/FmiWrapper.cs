using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using RGiesecke.DllExport; // Vereist de NuGet package: UnmanagedExports

namespace FMU.NET
{
    public static class FmiWrapper
    {
        // ==========================================================
        // FMI 2.0 C-INTERFACE IMPLEMENTATIE
        // Dit zijn de functies die Siemens NX daadwerkelijk aanroept.
        // ==========================================================

        private static int _instanceCounter = 0;
        private static Dictionary<IntPtr, WaferSlipDynamics> _instances = new Dictionary<IntPtr, WaferSlipDynamics>();

        [DllExport("fmi2Instantiate", CallingConvention = CallingConvention.Cdecl)]
        public static IntPtr fmi2Instantiate(
            string instanceName,
            int fmiType,
            string fmiGUID,
            string fmiResourceLocation,
            IntPtr functions,
            int visible,
            int loggingOn)
        {
            try
            {
                // Maak een nieuwe C# instantie
                var model = new WaferSlipDynamics();
                model.EnterInitializationMode(); // Pre-init

                // Genereer een unieke "Pointer" handle voor NX
                _instanceCounter++;
                IntPtr handle = new IntPtr(_instanceCounter);
                
                _instances[handle] = model;
                
                return handle;
            }
            catch (Exception)
            {
                return IntPtr.Zero; // Error
            }
        }

        [DllExport("fmi2FreeInstance", CallingConvention = CallingConvention.Cdecl)]
        public static void fmi2FreeInstance(IntPtr c)
        {
            if (_instances.ContainsKey(c))
            {
                _instances.Remove(c);
            }
        }

        [DllExport("fmi2SetupExperiment", CallingConvention = CallingConvention.Cdecl)]
        public static int fmi2SetupExperiment(IntPtr c, int toleranceDefined, double tolerance, double startTime, int stopTimeDefined, double stopTime)
        {
            if (_instances.TryGetValue(c, out var model))
            {
                model.SetupExperiment(startTime, stopTime, tolerance);
                return 0; // fmi2OK
            }
            return 3; // fmi2Error
        }

        [DllExport("fmi2EnterInitializationMode", CallingConvention = CallingConvention.Cdecl)]
        public static int fmi2EnterInitializationMode(IntPtr c)
        {
            if (_instances.TryGetValue(c, out var model))
            {
                model.EnterInitializationMode();
                return 0;
            }
            return 3;
        }

        [DllExport("fmi2ExitInitializationMode", CallingConvention = CallingConvention.Cdecl)]
        public static int fmi2ExitInitializationMode(IntPtr c)
        {
            if (_instances.TryGetValue(c, out var model))
            {
                model.ExitInitializationMode();
                return 0;
            }
            return 3;
        }

        [DllExport("fmi2DoStep", CallingConvention = CallingConvention.Cdecl)]
        public static int fmi2DoStep(IntPtr c, double currentCommunicationPoint, double communicationStepSize, int noSetFMUStatePriorToCurrentPoint)
        {
            if (_instances.TryGetValue(c, out var model))
            {
                model.DoStep(currentCommunicationPoint, communicationStepSize);
                return 0; // fmi2OK
            }
            return 3; // fmi2Error
        }

        // ==================== GETTERS & SETTERS (Variable Mapping) ====================
        
        [DllExport("fmi2GetReal", CallingConvention = CallingConvention.Cdecl)]
        public static int fmi2GetReal(IntPtr c, [In] uint[] vr, int nvr, [Out] double[] value)
        {
            if (!_instances.TryGetValue(c, out var model)) return 3;

            for (int i = 0; i < nvr; i++)
            {
                switch (vr[i])
                {
                    case 1: value[i] = model.AngularAcceleration; break;
                    case 4: value[i] = model.SlipFactor; break;
                    case 5: value[i] = model.MaxSafeAcceleration; break;
                    case 7: value[i] = model.MuFriction; break;
                    case 8: value[i] = model.SafetyMargin; break;
                    case 9: value[i] = model.NominalVacuumPressure; break;
                    default: return 2; // fmi2Warning (unknown variable)
                }
            }
            return 0;
        }

        [DllExport("fmi2SetReal", CallingConvention = CallingConvention.Cdecl)]
        public static int fmi2SetReal(IntPtr c, [In] uint[] vr, int nvr, [In] double[] value)
        {
            if (!_instances.TryGetValue(c, out var model)) return 3;

            for (int i = 0; i < nvr; i++)
            {
                switch (vr[i])
                {
                    case 1: model.AngularAcceleration = value[i]; break;
                    case 7: model.MuFriction = value[i]; break;
                    case 8: model.SafetyMargin = value[i]; break;
                    case 9: model.NominalVacuumPressure = value[i]; break;
                }
            }
            return 0;
        }

        [DllExport("fmi2GetInteger", CallingConvention = CallingConvention.Cdecl)]
        public static int fmi2GetInteger(IntPtr c, [In] uint[] vr, int nvr, [Out] int[] value)
        {
            if (!_instances.TryGetValue(c, out var model)) return 3;

            for (int i = 0; i < nvr; i++)
            {
                switch (vr[i])
                {
                    case 3: value[i] = model.WaferType; break;
                    default: return 2; 
                }
            }
            return 0;
        }

        [DllExport("fmi2SetInteger", CallingConvention = CallingConvention.Cdecl)]
        public static int fmi2SetInteger(IntPtr c, [In] uint[] vr, int nvr, [In] int[] value)
        {
            if (!_instances.TryGetValue(c, out var model)) return 3;

            for (int i = 0; i < nvr; i++)
            {
                switch (vr[i])
                {
                    case 3: model.WaferType = value[i]; break;
                }
            }
            return 0;
        }

        [DllExport("fmi2GetBoolean", CallingConvention = CallingConvention.Cdecl)]
        public static int fmi2GetBoolean(IntPtr c, [In] uint[] vr, int nvr, [Out] int[] value) // FMI booleans are int32
        {
            if (!_instances.TryGetValue(c, out var model)) return 3;

            for (int i = 0; i < nvr; i++)
            {
                switch (vr[i])
                {
                    case 2: value[i] = model.VacuumActive ? 1 : 0; break; // Input
                    case 6: value[i] = model.IsSlipping ? 1 : 0; break;   // Output
                    default: return 2;
                }
            }
            return 0;
        }

        [DllExport("fmi2SetBoolean", CallingConvention = CallingConvention.Cdecl)]
        public static int fmi2SetBoolean(IntPtr c, [In] uint[] vr, int nvr, [In] int[] value)
        {
            if (!_instances.TryGetValue(c, out var model)) return 3;

            for (int i = 0; i < nvr; i++)
            {
                switch (vr[i])
                {
                    case 2: model.VacuumActive = (value[i] != 0); break;
                }
            }
            return 0;
        }

        // Stub voor andere types (String) - vereist voor compliance
        [DllExport("fmi2GetString", CallingConvention = CallingConvention.Cdecl)]
        public static int fmi2GetString(IntPtr c, [In] uint[] vr, int nvr, [Out] IntPtr[] value) { return 0; }
        
        [DllExport("fmi2SetString", CallingConvention = CallingConvention.Cdecl)]
        public static int fmi2SetString(IntPtr c, [In] uint[] vr, int nvr, [In] IntPtr[] value) { return 0; }

        [DllExport("fmi2Terminate", CallingConvention = CallingConvention.Cdecl)]
        public static int fmi2Terminate(IntPtr c) { return 0; }
        
        [DllExport("fmi2Reset", CallingConvention = CallingConvention.Cdecl)]
        public static int fmi2Reset(IntPtr c) { return 0; }

        [DllExport("fmi2GetTypesPlatform", CallingConvention = CallingConvention.Cdecl)]
        public static IntPtr fmi2GetTypesPlatform() { return Marshal.StringToHGlobalAnsi("default"); }
        
        [DllExport("fmi2GetVersion", CallingConvention = CallingConvention.Cdecl)]
        public static IntPtr fmi2GetVersion() { return Marshal.StringToHGlobalAnsi("2.0"); }
    }
}