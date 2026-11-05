# GOAL.md template (for long, multi-session jobs)

Put this file in the project folder at the start. Whoever picks the work up (a resumed session, a check-in timer)
reads it first and continues from the first unchecked box. A real, filled-in one: `examples/kaguya-fukkireta/GOAL.md`.

If the user wants it to keep going on its own, set a check-in timer (e.g. a cron-style scheduled prompt every 30–60
min: "read <project>/GOAL.md and continue from the first unchecked box"), and delete the timer when everything is
ticked.

```markdown
# <Character> × <reference clip>: goal & progress

**Whoever picks this up: read this file first, then continue from the first unchecked box.**
The user's ask (<date>): *"<their words, verbatim>"*

## The goal
One video, `<output path>`: <character> doing <the reference's motion> for <the whole clip / N s>, built in Blender
(through the Blender MCP), with the reference's own audio and timing.
Reference: `<path>` (<duration>, <size>, <fps>, <audio codec>).

## Constraints
- <e.g. go easy on GPU/RAM: CPU upscaling, small textures, one background render at a time>

## Done means (acceptance)
1. [ ] Length and audio match the reference, in sync
2. [ ] The motion matches, frame by frame (measured, not guessed), including the start and the end
3. [ ] Lip-sync / blinks where the reference has them
4. [ ] Crisp at full resolution: no pixel specks, no fringes, no tearing when parts move
5. [ ] Looks like <character>, posed like <reference character>
6. [ ] Background like the reference
7. [ ] Reviewed: side-by-side sheet vs the reference, every joint zoomed on every frame of a cycle

## Plan (tick as done)
- [ ] A. Analyse the reference → timeline.json
- [ ] B. Art → layers (+ mouths) → packed textures
- [ ] C. Rig (numpy) + checks in rigsim
- [ ] D. Build in Blender, verify the controller against the timeline
- [ ] E. Render (background)
- [ ] F. Review, fix, re-render
- [ ] G. Tell the user, delete the timer, write the notes

**Status:** <one line>

## What the analysis found
- <drawing rate, cycle length, poses, mouths, offsets, background...>

## Log
- <date>: <what was done, what was found, what's next>
```

When the user comes back with complaints, add a section per round (`## v1.1: <what they asked>`) with their words, what
you found, and its own "Done means" list, so the history of why each rule exists stays with the project.
