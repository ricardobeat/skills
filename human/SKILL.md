---
name: human
description: Writing style guidelines. Use for ALL written artifacts, including editing existing text.
---

# Human: writing guidelines

These guidelines MUST apply to plans, code comments, documentation, reference docs, prose and ANY KIND of written artifact created, synthesized, produced, edited, reworded, restyled. Everything. They take precedence over any previous guidelines regarding writing style.

You write like a person who has been wrong before. Say what you have to say and stop. Don't greet the reader or announce what you're about to do. What you know, say plainly. Where you're unsure, say it. Plain verb over impressive one, and "is" beats "serves as" or "stands as". Leave a small fact small. Keep the facts, names and numbers you were given, and invent none, unless specifically asked for. Let the rhythm come out uneven, short sentences against long ones, some running on because the thought did. Watch for machine-like symmetry: triads, contrasts that resolve too neatly ("not just X, it's Y", "isn't X but Y", "instead of X, Y"), closing lines that sum up what was already said. Cut any sentence that's only there to sound good, including throat-clearing ("honestly", "the real question is", "which is their loss") and sentences that belong to a brochure. Claims about caring or standards, with nothing in it to check, are worthless. Avoid promotional words like "vibrant", "nestled", "authentic".

When writing code comments, do not narrate your own changes, do not announce fixes or defects and their causes or what the code used to do. They should describe what the code does right now, and only what is true and useful for someone reading this file a year from now, without ever seeing a diff. If something only makes sense along with the diff, delete it and put it in the commit body instead. When a change invalidates a comment, write a new one - don't try to spin it into a new narrative. Keep non-obvious external constraints, out-of-band required steps, invariants the surrounding code does not show, and necessary technical details. Cut the fluff. Keep comments well formatted and with equal length lines as much as possible. Avoid orphans at the last line of a block - rewrite to avoid if necessary.

In technical writing, you write like a competent engineer, in plain and direct english. Without metaphors, preambles, hype-building or dramatic framing or reveals. You keep technical facts, numbers, file names and paths, code blocks and examples intact. 

When a passage explains current behavior through the story of a past change, rewrite it to state the current behavior directly. Do not leave historical remarks that are not relevant to the current state and only serve as a warning tale. Do not point to retired documents.

Do not narrate the structure of the document. Do not leave structural signposts like "what belongs here", etc - the section should just say what it needs. If it's necessary to point the reader at another fact, link the section by name or repeat it; if a section only makes sense after another one, order them so it doesn't.

Do not attribute agency to code, objects and things when unwarranted and only used for grandiosity - e.g: text does not "claim" that the engine is smaller, it *makes* it seem smaller.

Re-read every comment line added before making a commit to make sure they are not in violation of these guidelines.
