#include <CoreAudio/CoreAudio.h>

int is_audio_playing() {
    AudioDeviceID deviceID = kAudioObjectUnknown;
    UInt32 size = sizeof(deviceID);

    AudioObjectPropertyAddress defaultDevice = {
        kAudioHardwarePropertyDefaultOutputDevice,
        kAudioObjectPropertyScopeGlobal,
        kAudioObjectPropertyElementMaster
    };

    if (AudioObjectGetPropertyData(kAudioObjectSystemObject, &defaultDevice, 0, NULL, &size, &deviceID) != noErr)
        return 0;

    // We still use DeviceIsRunningSomewhere, but add volume check
    UInt32 isRunning = 0;
    size = sizeof(isRunning);

    AudioObjectPropertyAddress runningProp = {
        kAudioDevicePropertyDeviceIsRunningSomewhere,
        kAudioDevicePropertyScopeOutput,
        kAudioObjectPropertyElementMaster
    };

    if (AudioObjectGetPropertyData(deviceID, &runningProp, 0, NULL, &size, &isRunning) != noErr || !isRunning)
        return 0;

    // ALSO check volume to guess activity
    Float32 volume = 0.0;
    size = sizeof(volume);

    AudioObjectPropertyAddress volumeProp = {
        kAudioDevicePropertyVolumeScalar,
        kAudioDevicePropertyScopeOutput,
        0 // left channel
    };

    if (AudioObjectHasProperty(deviceID, &volumeProp) &&
        AudioObjectGetPropertyData(deviceID, &volumeProp, 0, NULL, &size, &volume) == noErr) {
        if (volume == 0.0f) return 0; // muted
    }

    return 1; // running and volume is nonzero
}
