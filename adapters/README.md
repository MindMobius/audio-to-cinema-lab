# Adapters

Adapters translate a stable Lab artifact contract into a concrete local tool or service.

Each adapter belongs in its own directory and should provide:

1. a short README describing inputs, outputs and capability limits;
2. a configuration example with secrets omitted;
3. a versioned runner or documented command;
4. a JSON receipt for every run;
5. tests that do not require private media, plus an integration test when the tool is available.

The first migrated project records ComfyUI, Whisper, HTDemucs, FFmpeg and HyperFrames as production tools. Their complete machine-specific environments remain outside the public repository.
