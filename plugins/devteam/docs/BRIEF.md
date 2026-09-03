# The original brief

The author's statement of the idea, preserved verbatim as the thing every later
document answers to. It is not maintained — where it and
[`../DESIGN.md`](../DESIGN.md) disagree, the design is current and the
disagreement should be a recorded decision, not a silent edit here.

The three departures made deliberately during design, each recorded in
[`../DESIGN.md`](../DESIGN.md) §12:

1. the state directory is `devteam/` and **tracked**, not a hidden
   `.claude-skills/`, because the design record is worth reviewing in a pull
   request and its git history is the record of how the product's definition
   changed;
2. escalations are classified by **reversibility**, so the loop can proceed
   on a recommendation for a reversible question rather than idling on it;
3. the repository is a plugin **marketplace**, and this pipeline is the first
   plugin in it, so later workflows drop in beside it.

---

```
DO NOT MODIFY ANYTHING OUTSIDE OF ~/Workspace/REPOS/claude-skills WITHOUT EXPLICIT PERMISSION!!
OTHER PROJECTS/SESSIONS ARE ONGOING AND WE CANNOT INTERUPT THEM!!

I want to build a development pipeline type deal out of agents and skills.
I have already created a repo and github and cloned it (REPOS/claude-skills) but
thats about it and it still needs to be setup fully with github keywords and the 
readme filled in and .gitignore finished and all that jazz. 
What i am actually looking to do is sort of model a real world flow from client 
with an idea to functioning product, at least from the development end of things. 
I want this to be generalizable to pretty much any software engineering project.
It needs to be very thorough and specific and not leave anything to assumption.
Needs to include any relevant structures (like directories or files or scripts
the agents may use or need for sharing). It needs to include defined checkpoints 
in the process to make sure things are not diverging from the design and that the 
design still meets the project goals. It needs to be able to operate with as 
little user input as possible outside of the initial planning stages, 
planned checkpoints, and final review so initial setup stages should seek to 
obtain the required permissions (no more/no less) in the beginning to allow for
this.Of course there will be times where continuing without user input will
not be possible and we will account for that in our plan.we should really think
about this well and take all the time we need researching and planning it. 

so, my thoughts were that it could be layered like so:
- copy repo to project
- run setup script
  - creates a .claude-skills directory to hold all the information and structures
    and settings and communication paths/methods for workers and project status
    systems and boards and locks and all that good stuff.
  - prints out instructions to start onboarding process
  - user initiates onboarding which invokes project manager to take over   


----- AGENTS/SKILLS ------------------------------------------------------------
Project Manager Agent/Skill
 - Takes the initial idea from the user and refines it via research and
   grilling the user about any details that are ambiguous or need more details.
 - generates a high level plan divided into 'tasks'
 - Defines the initial layout/scope of the project and does local and github end
   setup for the project if neccessary. 
 - Keeps track of all ongoing 'tasks' in a project.
 - can query state of tasks and update user when requested
 - can start/resume the project loop from a new session
 - will relay relevant questions from task supervisors back up to the user and explain
   them with reserach/test backed recommendations when possible
 - coordinate things between tasks as neccessary, faciliate communication
   between tasks as neccessary
 - ensure all project constraints and standards are maintained at all times

Supervisor Agent/Skill
 - Does not interact with user directly 
 - Manages a task
 - Spawns and monitors skilled workers as required
 - Determines appropriate model to use based on task complexity and project 
   minimum/maximum model constraints to improve speed and token efficiency
 - Trys to keep going until task is complete or something is blocking 
   progress
 - Escalate all relevant questions/blockers from workers to project manager
   layer if it cannot resolve them itself from project constraints/goals or 
   research
 - Verifies the output of workers, never trust them blindly
 - Can report current status of project at any time if queried by project
   manager

Worker Agents/Skills
 - Does not interact with user directly
 - Reports to a supervisor and follows its commands exactly
 - Escalate any questions or problems it has that need resolution to
   its supervisor if they cannot be resolved via project constraints/goals or
   research
 - Types
   - Interviewer/Onboarder (really grill the user about the project constraints
     and requirements and any info we cannot get from research or testing or
     best practices alone. 
   - Planner (Create the granular and specific plans for a project roadmap and
     review any requested changes to plans to make sure they mesh up and things
     don't get out of whack)
   - Researcher (perform various research tasks)
   - Implementer (turn plans into working code)
   - Auditors (Do deep dives into code looking for any problems including 
     bugs/security issues including recently discovered attack vectors that 
     will need to be researched to discover)
     - Hygiene/Code Format
     - Safety/Security
     - Correctness
   - Tester  (performs various testing tasks in sandbox environment
   - Documenter (create and keep up to date all project documentation)
   - Reviewer (review and manage pull requests)
   
I am always open to suggestions and improvements regarding any of it. 
Lets reserach and brainstorm and plan this out well so we can make this as 
awesome as we can make it. 
  
```
