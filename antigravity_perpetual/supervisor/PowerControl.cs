using System;
using System.Runtime.InteropServices;

namespace AntigravityPerpetual
{
    public static class PowerControl
    {
        [Flags]
        public enum EXECUTION_STATE : uint
        {
            ES_AWAYMODE_REQUIRED = 0x00000040,
            ES_CONTINUOUS        = 0x80000000,
            ES_DISPLAY_REQUIRED  = 0x00000002,
            ES_SYSTEM_REQUIRED   = 0x00000001
        }

        [DllImport("kernel32.dll", CharSet = CharSet.Auto, SetLastError = true)]
        public static extern EXECUTION_STATE SetThreadExecutionState(EXECUTION_STATE esFlags);

        public static uint PreventSleep(bool allowDisplaySleep = true)
        {
            EXECUTION_STATE flags = EXECUTION_STATE.ES_CONTINUOUS | EXECUTION_STATE.ES_SYSTEM_REQUIRED | EXECUTION_STATE.ES_AWAYMODE_REQUIRED;
            if (!allowDisplaySleep)
            {
                flags |= EXECUTION_STATE.ES_DISPLAY_REQUIRED;
            }
            return (uint)SetThreadExecutionState(flags);
        }

        public static uint RestoreSleep()
        {
            return (uint)SetThreadExecutionState(EXECUTION_STATE.ES_CONTINUOUS);
        }
    }
}
