#include <cmajor/API/cmaj_Engine.h>

#include <fstream>
#include <iostream>
#include <sstream>
#include <string>

int main (int argc, char** argv)
{
    if (argc < 3)
    {
        std::cerr << "usage: cmajor_fixture_compiler <libCmajPerformer> <fixture>...\n";
        return 2;
    }

    if (! cmaj::Library::initialise (argv[1]))
    {
        std::cerr << "failed to load exact Cmajor runtime: " << argv[1] << "\n";
        return 2;
    }

    bool allPassed = true;
    for (int i = 2; i < argc; ++i)
    {
        const std::string path = argv[i];
        std::ifstream input (path, std::ios::binary);
        const bool opened = input.is_open();
        std::ostringstream buffer;
        buffer << input.rdbuf();

        cmaj::DiagnosticMessageList messages;
        cmaj::Program program;
        auto engine = cmaj::Engine::create();
        engine.setBuildSettings (cmaj::BuildSettings().setFrequency (48000).setSessionID (3175 + i));

        const bool parsed = opened && program.parse (messages, path, buffer.str());
        const bool loaded = parsed && engine.load (messages, program, {}, {});
        const bool linked = loaded && engine.link (messages);

        if (! linked)
        {
            allPassed = false;
            std::cerr << "FAIL " << path << "\n" << messages.toString() << "\n";
        }
        else
        {
            std::cout << "PASS " << path << "\n";
        }
    }

    return allPassed ? 0 : 1;
}
