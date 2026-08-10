# VN music cue design

## Start from dramatic function

Describe what the player should feel and notice, not only genre. Useful functions include curiosity, awkward comedy, procedural tension, emotional distance, reveal, reconciliation, and comic failure.

For every cue record:

- scene IDs and entry condition;
- narrative function and mood words;
- BPM range and energy from 0 to 1;
- loop or one-shot behavior;
- whether it continues across a scene transition;
- stop, fade, or replacement behavior;
- whether silence is allowed or required.

## Keep a coherent score

Reuse motifs, intervals, rhythm cells, and instrument roles across related tracks. Change tempo, mode, register, or density to transform the motif for a new emotional context.

Avoid one track per visual cut. Reuse a cue when the dramatic function is unchanged; switch music only when the player's interpretation should change.

## Write for dialogue

Keep the melodic range and drum density below the dialogue rhythm. Leave rests. Avoid a bright high-register pulse on every step. Use stronger drums for short tension peaks, not continuous conversation.

Treat silence as a cue. A reveal can be clearer after stopping music than after adding another busy track.

## Acceptance

- Every scene has a declared cue or intentional silence.
- Cue changes align with narrative changes, not background changes alone.
- Tracks have distinct functions but share a score identity.
- Loop length supports the likely reading time.
- Entry and exit behavior is implementable in GB Studio events.
