# Reporting a problem

One report per problem, in this shape. It is short on purpose — the goal is
something diagnosable, not something polished.

```
FINDING <n> — <one line: what is wrong, not what you were doing>

what I did:        the command, skill or step, exactly
what I expected:   and where that expectation came from — quote the skill
                   or document if there is one
what happened:     verbatim output where there is any
worked around it:  yes, how | no, I stopped
how much it cost:  a guess is fine — minutes, or "I nearly gave up"
```

## What makes a report useful

**Quote the document you were following.** The most valuable findings so far
were contradictions between two things the pipeline says, not code that
misbehaved. If a skill told you to do something and a check then refused it,
that pair is the finding — and only you can see both halves.

**Say whether you worked around it.** A defect you routed around is more
dangerous than one that stopped you, because nothing else will ever notice it.

**Report near misses.** "I nearly re-dispatched a task that was still running,
and only didn't because I happened to see the child agent" is a real finding.
The one that stopped you is a bug; the one you nearly hit is a design flaw.

**Report the boring ones.** A confusing message, a step whose purpose you could
not work out, a check whose output you ignored. Small friction compounds and it
is invisible to whoever wrote the thing.

## Three kinds, and we want all three

| Kind | Looks like |
|---|---|
| **broken** | it errored, refused, or produced something wrong |
| **wrong** | it worked, and the result was not what the document promised |
| **unnecessary** | it worked, and buying it was not worth what it cost |

The third is the one we have never received and most need. **Everything found
so far has made this pipeline stricter and nothing has made it simpler.** If a
requirement, a check, a gate or a whole skill earned nothing on your project,
that is a finding, and it is worth more than another edge case.

## Before you report a defect in something you did not write, re-read its source

The most expensive wrong finding in this project's history was built like
this: a document was read as far as line 19, a premise was formed, and then
four further steps of good reasoning were built outward from it — a workaround
constructed, a theory derived, a finding written blaming somebody's fix. The
answer was on **line 22 of the same file**, and none of the four steps was "go
back and check the premise".

That failure is invisible from inside, because every step after the first is
sound. The tell is structural rather than technical: **if your finding requires
the other person to have overlooked something obvious, re-read their source
before you send it.** They may well have; but the cheaper hypothesis is that
you stopped reading too early, and it costs one minute to eliminate.

Withdrawing a finding after checking is not an embarrassment — it is frequently
how the real one surfaces, and it is worth more to us than a finding that was
right by luck.

## What not to do

- **Do not fix the pipeline.** It is not yours and a fix hides the finding.
- **Do not tidy a bad report into a good one.** Verbatim output beats a clean
  summary; the detail you thought was noise is often the diagnosis.
- **Do not batch a week of friction into one message at the end.** By then the
  specifics are gone, and the specifics are the whole value.
