#include <cmajor/API/cmaj_Engine.h>

#include <algorithm>
#include <cmath>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

namespace
{
constexpr uint32_t sampleRate = 48000;

struct Scenario
{
    const char* name;
    float initialBpm;
    float changedBpm;
    uint32_t changeFrame;
    int divisionIndex;
    bool playing;
    uint32_t expectedEchoFrame;
};

bool runScenario (const std::string& sourcePath,
                  const std::string& source,
                  const Scenario& scenario,
                  uint32_t sessionID)
{
    cmaj::DiagnosticMessageList messages;
    cmaj::Program program;
    auto engine = cmaj::Engine::create();
    engine.setBuildSettings (cmaj::BuildSettings().setFrequency (sampleRate).setSessionID (sessionID));

    if (! program.parse (messages, sourcePath, source)
        || ! engine.load (messages, program, {}, {}))
    {
        std::cerr << "FAIL " << scenario.name << " compile\n" << messages.toString() << "\n";
        return false;
    }

    const auto inputHandle = engine.getEndpointHandle ("in");
    const auto outputHandle = engine.getEndpointHandle ("out");
    const auto transportHandle = engine.getEndpointHandle ("transportIn");
    const auto divisionHandle = engine.getEndpointHandle ("param1");
    const auto feedbackHandle = engine.getEndpointHandle ("param2");
    const auto mixHandle = engine.getEndpointHandle ("param3");

    if (! engine.link (messages))
    {
        std::cerr << "FAIL " << scenario.name << " link\n" << messages.toString() << "\n";
        return false;
    }

    auto performer = engine.createPerformer();
    const uint32_t totalFrames = scenario.expectedEchoFrame + 1024;
    const uint32_t blockSizes[] = { 31, 64, 127, 257, 511 };
    uint32_t blockIndex = 0;
    uint32_t framesDone = 0;
    double ppq = 0.0;
    uint32_t peakFrame = 0;
    float peak = 0.0f;
    bool parameterEventsSent = false;

    while (framesDone < totalFrames)
    {
        uint32_t framesThisBlock = std::min (blockSizes[blockIndex++ % 5], totalFrames - framesDone);
        if (scenario.changeFrame > framesDone && scenario.changeFrame < framesDone + framesThisBlock)
            framesThisBlock = scenario.changeFrame - framesDone;

        const float bpm = scenario.changedBpm > 0.0f && framesDone >= scenario.changeFrame
                        ? scenario.changedBpm : scenario.initialBpm;
        performer.setBlockSize (framesThisBlock);

        if (! parameterEventsSent)
        {
            performer.addInputEvent (divisionHandle, 0, float (scenario.divisionIndex));
            performer.addInputEvent (feedbackHandle, 0, 0.0f);
            performer.addInputEvent (mixHandle, 0, 1.0f);
            parameterEventsSent = true;
        }

        performer.addInputEvent (transportHandle, 0, scenario.playing ? 1.0f : 0.0f);
        performer.addInputEvent (transportHandle, 0, bpm);
        performer.addInputEvent (transportHandle, 0, 4.0f);
        performer.addInputEvent (transportHandle, 0, 4.0f);
        performer.addInputEvent (transportHandle, 0, float (ppq));
        performer.addInputEvent (transportHandle, 0, float (std::floor (ppq / 4.0) * 4.0));

        std::vector<float> input (static_cast<size_t> (framesThisBlock) * 2, 0.0f);
        if (framesDone == 0)
            input[0] = input[1] = 1.0f;
        performer.setInputFrames (inputHandle, input.data(), framesThisBlock);
        performer.advance();

        std::vector<float> output (static_cast<size_t> (framesThisBlock) * 2, 0.0f);
        performer.copyOutputFrames (outputHandle, output.data(), framesThisBlock);
        for (uint32_t frame = 0; frame < framesThisBlock; ++frame)
        {
            const float magnitude = std::max (std::abs (output[frame * 2]),
                                              std::abs (output[frame * 2 + 1]));
            if (magnitude > peak)
            {
                peak = magnitude;
                peakFrame = framesDone + frame;
            }
        }

        if (scenario.playing)
            ppq += double (framesThisBlock) * double (bpm) / 60.0 / double (sampleRate);
        framesDone += framesThisBlock;
    }

    const bool passed = peak > 0.99f && peakFrame == scenario.expectedEchoFrame;
    std::cout << (passed ? "PASS " : "FAIL ") << scenario.name
              << " expected=" << scenario.expectedEchoFrame
              << " measured=" << peakFrame << " peak=" << peak << "\n";
    return passed;
}
}

int main (int argc, char** argv)
{
    if (argc != 3)
    {
        std::cerr << "usage: cmajor_transport_sync_runner <libCmajPerformer> <fixture>\n";
        return 2;
    }

    if (! cmaj::Library::initialise (argv[1]))
    {
        std::cerr << "failed to load exact Cmajor runtime: " << argv[1] << "\n";
        return 2;
    }

    std::ifstream input (argv[2], std::ios::binary);
    std::ostringstream buffer;
    buffer << input.rdbuf();
    if (! input.is_open())
    {
        std::cerr << "failed to read fixture: " << argv[2] << "\n";
        return 2;
    }

    const Scenario scenarios[] = {
        { "quarter-note at 120 BPM", 120.0f, 0.0f, 0, 2, true, 24000 },
        { "quarter-note at 60 BPM", 60.0f, 0.0f, 0, 2, true, 48000 },
        { "dotted-eighth at 120 BPM", 120.0f, 0.0f, 0, 6, true, 18000 },
        { "stopped transport retains host delay length", 90.0f, 0.0f, 0, 2, false, 32000 },
        { "tempo automation applies on next packet", 120.0f, 60.0f, 8192, 2, true, 48000 },
    };

    bool allPassed = true;
    uint32_t sessionID = 9000;
    for (const auto& scenario : scenarios)
        allPassed = runScenario (argv[2], buffer.str(), scenario, sessionID++) && allPassed;
    return allPassed ? 0 : 1;
}
