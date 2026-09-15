"""
Deterministic Interview Controller — Easy / Medium / High tiered engine.

This owns every interview-flow decision (no LLM involved in deciding what
happens next — only in phrasing it, via interview_manager.py). This is
intentional: earlier testing showed that asking an LLM to track retry
counts / tier progress purely from conversation history caused it to drift
(e.g. re-asking the same question forever). All counting and branching
below is plain Python.

============================================================================
RULES IMPLEMENTED
============================================================================

Applies to: Programming Languages, Libraries/Frameworks, Tools (each
individual skill), and Projects (after the fixed opening question). NOT
applied to Personal Information or Reasoning, which keep a simpler
one-retry-with-hint pattern (unchanged from before).

EASY tier (per skill/topic):
    - Ask exactly 4 easy questions. No hints. Always a fresh question.
    - Count how many of the 4 were answered CORRECTLY.
    - >= 2 correct  -> move to MEDIUM tier (full budget).
    - <  2 correct  -> ask ONE probe question at medium level:
          - correct  -> continue in MEDIUM tier (this probe counts as
            medium question #1).
          - wrong    -> this skill's interview ends here. Move to the
            next skill/topic. (Does NOT terminate the whole interview.)

MEDIUM tier:
    - Ask up to 5 questions total (the probe above counts as #1 if it was
      used). For each answer, based on Agent 6's analysis:
          - correct         -> ask a NEW (different) question next.
          - partial-correct -> ask a SIMILAR question on the same
            sub-topic (no hint).
          - wrong           -> ask a NEW (different) question next
            (not a retry).
    - After the 5-question medium budget is used, count total correct:
          - correct_count >= 4        -> HIGH tier, budget = 5 questions.
          - correct_count in (2, 3)   -> HIGH tier, budget = correct_count.
          - correct_count <= 1        -> this skill's interview ends here.
            Move to the next skill/topic.

HIGH tier (budget set above: 2, 3, or 5):
    - Same per-question routing as medium, EXCEPT the partial-correct case
      now includes a hint:
          - correct         -> new question.
          - partial-correct -> HINT + a similar question on the same
            sub-topic.
          - wrong           -> new question (no hint, no retry).
    - After the tier's budget is used, this skill's interview ends. Move
      to the next skill/topic.

PROJECTS step:
    - First question is always fixed: "Please explain your project."
    - After that, the SAME Easy -> Medium -> High engine above runs for
      the project discussion (one tracker representing "the project"),
      using the resume's project context for question content.

PERSONAL INFORMATION / REASONING (unchanged):
    - Wrong/irrelevant answer on the 1st attempt -> retry the same
      question WITH a hint. Still wrong on the 2nd attempt -> move on
      regardless.

CROSS-CUTTING:
    - Offensive language increments a warning counter; a second offense
      terminates the WHOLE interview (this is the only remaining
      whole-interview termination path — failing a skill no longer does).
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

CORRECT = "correct"
PARTIAL = "partial"
WRONG = "wrong"

EASY_BUDGET = 4
MEDIUM_BUDGET = 5


def classify(evaluation_report) -> str:
    """Turns Agent 6's EvaluationReport into correct / partial / wrong."""
    if evaluation_report is None:
        return WRONG
    if not getattr(evaluation_report, "relevant_answer", False):
        return WRONG
    tech = getattr(evaluation_report, "technically_correct", False)
    logic = getattr(evaluation_report, "logically_correct", False)
    if tech and logic:
        return CORRECT
    if tech or logic:
        return PARTIAL
    return WRONG


@dataclass
class SkillTracker:
    name: str
    mandatory: bool = False
    context_type: str = "skill"  # "skill" | "project"

    tier: str = "easy"  # easy | probe | medium | high
    easy_asked: int = 0
    easy_correct: int = 0
    medium_asked: int = 0
    medium_correct: int = 0
    high_asked: int = 0
    high_correct: int = 0
    high_budget: int = 0

    last_correctness: Optional[str] = None
    done: bool = False

    def advance(self, last_eval):
        """Updates state based on the evaluation of the most recently
        asked question for this tracker. Call BEFORE asking the next one."""
        if last_eval is None:
            return
        correctness = classify(last_eval)
        self.last_correctness = correctness

        if self.tier == "easy":
            if correctness == CORRECT:
                self.easy_correct += 1
            if self.easy_asked >= EASY_BUDGET:
                self.tier = "medium" if self.easy_correct >= 2 else "probe"
            return

        if self.tier == "probe":
            if correctness == CORRECT:
                self.medium_correct = 1
                self.medium_asked = 1
                self.tier = "medium"
            else:
                self.done = True
            return

        if self.tier == "medium":
            if correctness == CORRECT:
                self.medium_correct += 1
            if self.medium_asked >= MEDIUM_BUDGET:
                if self.medium_correct >= 4:
                    self.high_budget = 5
                    self.tier = "high"
                elif self.medium_correct >= 2:
                    self.high_budget = self.medium_correct
                    self.tier = "high"
                else:
                    self.done = True
            return

        if self.tier == "high":
            if correctness == CORRECT:
                self.high_correct += 1
            if self.high_asked >= self.high_budget:
                self.done = True
            return

    def next_question_fields(self) -> Optional[Dict[str, Any]]:
        """Returns {"action", "tier", "give_hint"} for the next question to
        ask, and increments the relevant asked-counter. Returns None if the
        tracker is already done (caller should move to the next tracker)."""
        if self.done:
            return None

        if self.tier == "easy":
            self.easy_asked += 1
            action = "ASK_EASY_QUESTION" if self.easy_asked == 1 else "ASK_ANOTHER_EASY_QUESTION"
            return {"action": action, "tier": "easy", "give_hint": False}

        if self.tier == "probe":
            return {"action": "ASK_PROBE_QUESTION", "tier": "medium", "give_hint": False}

        if self.tier == "medium":
            if self.medium_asked == 0:
                self.medium_asked += 1
                return {"action": "ASK_MEDIUM_QUESTION", "tier": "medium", "give_hint": False}
            self.medium_asked += 1
            if self.last_correctness == PARTIAL:
                return {"action": "ASK_SIMILAR_MEDIUM_QUESTION", "tier": "medium", "give_hint": False}
            return {"action": "ASK_NEXT_MEDIUM_QUESTION", "tier": "medium", "give_hint": False}

        if self.tier == "high":
            if self.high_asked == 0:
                self.high_asked += 1
                return {"action": "ASK_HIGH_QUESTION", "tier": "high", "give_hint": False}
            self.high_asked += 1
            if self.last_correctness == PARTIAL:
                return {"action": "ASK_SIMILAR_HIGH_QUESTION_WITH_HINT", "tier": "high", "give_hint": True}
            return {"action": "ASK_NEXT_HIGH_QUESTION", "tier": "high", "give_hint": False}

        return None

    def score(self) -> float:
        total_correct = self.easy_correct + self.medium_correct + self.high_correct
        total_asked = self.easy_asked + self.medium_asked + self.high_asked
        return round(total_correct / total_asked * 100, 1) if total_asked else 0.0


def build_skill_trackers(skill_plans: List[dict]) -> List[SkillTracker]:
    return [
        SkillTracker(name=sp["skill_name"], mandatory=sp.get("mandatory", False), context_type="skill")
        for sp in (skill_plans or [])
    ]


class InterviewController:
    def __init__(self, interview_plan: dict):
        self.plan = interview_plan
        self.step_plans = {sp["step_number"]: sp for sp in interview_plan.get("step_plan", [])}

        # Step 1 - Personal Information (unchanged simple pattern)
        self.personal_topics = self._topics_for(1, default=["Introduction and Background"])
        self.personal_index = 0
        self.personal_attempt = 1

        # Steps 2/3/4 - skill-based, new tiered engine
        self.skill_lists = {
            2: build_skill_trackers(interview_plan.get("programming_languages", [])),
            3: build_skill_trackers(interview_plan.get("libraries_frameworks", [])),
            4: build_skill_trackers(interview_plan.get("tools", [])),
        }
        self.skill_index = {2: 0, 3: 0, 4: 0}

        # Step 5 - Projects: fixed opener, then the same tiered engine
        self.project_intro_done = False
        self.project_tracker = SkillTracker(name="Project Discussion", mandatory=False, context_type="project")

        # Step 6 - Reasoning (unchanged simple pattern)
        self.reasoning_topics = interview_plan.get("reasoning_topics", []) or ["General problem solving"]
        self.reasoning_budget = self._estimated_reasoning_questions()
        self.reasoning_index = 0
        self.reasoning_asked = 0
        self.reasoning_attempt = 1

        self.current_step = 1
        self.terminated = False
        self.completed = False
        self.termination_reason = None
        self.warning_count = 0

    # ---- helpers -----------------------------------------------------

    def _topics_for(self, step_number: int, default: List[str]) -> List[str]:
        sp = self.step_plans.get(step_number)
        if sp and sp.get("topics"):
            return sp["topics"]
        return default

    def _estimated_reasoning_questions(self) -> int:
        return max(len(self.reasoning_topics), 3)

    def _step_name(self, step_number: int) -> str:
        names = {
            1: "Personal Information", 2: "Programming Languages",
            3: "Libraries / Frameworks", 4: "Tools", 5: "Projects", 6: "Reasoning",
        }
        return names.get(step_number, "Unknown")

    def _directive(self, action: str, **kwargs) -> Dict[str, Any]:
        d = {
            "action": action,
            "step_number": self.current_step,
            "step_name": self._step_name(self.current_step),
            "skill_name": None,
            "topic": None,
            "tier": None,
            "context_type": None,
            "mandatory": False,
            "give_hint": False,
            "terminate": False,
            "termination_reason": None,
            "complete": False,
            "issue_warning": self.warning_count == 1,
        }
        d.update(kwargs)
        return d

    def _advance_step(self):
        self.current_step += 1
        if self.current_step > 6:
            self.completed = True

    def _register_warning(self, last_eval) -> bool:
        if last_eval is not None and getattr(last_eval, "offensive_language", False):
            self.warning_count += 1
            if self.warning_count >= 2:
                self.terminated = True
                self.termination_reason = "Offensive behaviour continued after a warning."
                return True
        return False

    # ---- main entry point ---------------------------------------------

    def next_action(self, last_evaluation=None) -> Dict[str, Any]:
        if self.terminated:
            return self._directive("TERMINATE", terminate=True, termination_reason=self.termination_reason)
        if self._register_warning(last_evaluation):
            return self._directive("TERMINATE", terminate=True, termination_reason=self.termination_reason)

        if self.current_step == 1:
            return self._handle_personal(last_evaluation)
        elif self.current_step in (2, 3, 4):
            return self._handle_skill_step(last_evaluation)
        elif self.current_step == 5:
            return self._handle_project(last_evaluation)
        elif self.current_step == 6:
            return self._handle_reasoning(last_evaluation)
        else:
            self.completed = True
            return self._directive("INTERVIEW_COMPLETE", complete=True)

    # ---- Step 1: Personal Information (unchanged) -----------------------

    def _handle_personal(self, last_eval):
        if last_eval is not None:
            correctness = classify(last_eval)
            if correctness == WRONG and self.personal_attempt == 1:
                self.personal_attempt = 2
                return self._directive(
                    "RETRY_PERSONAL_WITH_HINT",
                    topic=self.personal_topics[self.personal_index], give_hint=True,
                )
            self.personal_index += 1
            self.personal_attempt = 1

        if self.personal_index >= len(self.personal_topics):
            self._advance_step()
            return self.next_action(None)

        return self._directive("ASK_PERSONAL_QUESTION", topic=self.personal_topics[self.personal_index])

    # ---- Steps 2/3/4: skill-based, Easy -> Medium -> High ----------------

    def _handle_skill_step(self, last_eval):
        step = self.current_step
        trackers = self.skill_lists[step]
        idx = self.skill_index[step]

        if idx >= len(trackers):
            self._advance_step()
            return self.next_action(None)

        tracker = trackers[idx]
        tracker.advance(last_eval)

        if tracker.done:
            self.skill_index[step] += 1
            return self.next_action(None)

        fields = tracker.next_question_fields()
        if fields is None:
            self.skill_index[step] += 1
            return self.next_action(None)

        return self._directive(
            fields["action"],
            skill_name=tracker.name, tier=fields["tier"], context_type="skill",
            mandatory=tracker.mandatory, give_hint=fields["give_hint"],
        )

    # ---- Step 5: Projects — fixed opener, then Easy -> Medium -> High ----

    def _handle_project(self, last_eval):
        if not self.project_intro_done:
            if last_eval is not None:
                # This was the answer to "Please explain your project" —
                # used as context by Agent 5 for follow-ups, not scored
                # via the tier engine.
                self.project_intro_done = True
            else:
                return self._directive("PROJECT_INTRO", context_type="project")

        tracker = self.project_tracker
        tracker.advance(last_eval if self.project_intro_done and tracker.easy_asked > 0 else None)

        if tracker.done:
            self._advance_step()
            return self.next_action(None)

        fields = tracker.next_question_fields()
        if fields is None:
            self._advance_step()
            return self.next_action(None)

        return self._directive(
            fields["action"],
            skill_name=tracker.name, tier=fields["tier"], context_type="project",
            give_hint=fields["give_hint"],
        )

    # ---- Step 6: Reasoning (unchanged) -----------------------------------

    def _handle_reasoning(self, last_eval):
        difficulty_lean = None
        if last_eval is not None:
            correctness = classify(last_eval)
            if correctness == WRONG and self.reasoning_attempt == 1:
                self.reasoning_attempt = 2
                return self._directive(
                    "RETRY_REASONING_WITH_HINT", topic=self._current_reasoning_topic(), give_hint=True,
                )
            difficulty_lean = "harder" if correctness == CORRECT else "easier"
            self.reasoning_asked += 1
            self.reasoning_attempt = 1
            self.reasoning_index += 1

        if self.reasoning_asked >= self.reasoning_budget or self.reasoning_index >= len(self.reasoning_topics):
            self._advance_step()
            return self.next_action(None)

        return self._directive(
            "ASK_REASONING_QUESTION", topic=self._current_reasoning_topic(), difficulty_lean=difficulty_lean,
        )

    def _current_reasoning_topic(self) -> str:
        if not self.reasoning_topics:
            return "General problem solving"
        return self.reasoning_topics[self.reasoning_index % len(self.reasoning_topics)]
