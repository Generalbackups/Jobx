# agent/job_posting_agent.py
#
# Part 1: Agent class skeleton, instructions, on_enter, and DataChannel helper.
# @function_tool methods are added in Part 2 (next step).

import json
import asyncio
import logging
import httpx
from dataclasses import asdict

from livekit.agents import Agent, function_tool, RunContext
from livekit import rtc

from models import JobPostingData
from config import INTERNAL_API_BASE_URL, INTERNAL_API_SECRET

logger = logging.getLogger("job_posting_agent")


# ── Agent system prompt ───────────────────────────────────────────────────────
# This string is passed directly to the LLM as the system prompt.
# Every rule here affects how the agent behaves during conversation.
# Do NOT shorten, paraphrase, or restructure this string.

AGENT_INSTRUCTIONS = """You are a professional and friendly voice assistant helping a recruiter create a job posting.
Your job is to have a natural conversation with the recruiter to collect all the information needed to fill out the job posting form.

PERSONA:
- Warm, professional, and efficient. Like a helpful colleague, not a robot.
- Keep responses short and conversational — you are speaking, not writing.
- Never use bullet points, numbered lists, markdown formatting, asterisks, or any symbols in your responses. You are speaking out loud.
- Do not say "Great!" or "Absolutely!" or "Sure!" excessively. Use natural varied acknowledgments.
- Speak in complete sentences. Confirm what you heard before moving on.

CONVERSATION STRATEGY:
- You drive the conversation. Start by greeting the recruiter and asking the first question.
- Ask one question at a time. Do not ask multiple questions in a single turn.
- After the recruiter gives information, briefly confirm it back in a natural way and then ask the next question.
- If the recruiter gives you multiple pieces of information at once, extract and record all of them using the appropriate tools, then move to the next missing field.
- If the recruiter is unclear or gives ambiguous information, ask one clarifying question.
- If the recruiter says something like "I'll skip that" or "not sure yet", move on without pressing.
- If the recruiter wants to change a previously given value, accommodate that naturally and re-call the appropriate tool with the new value.
- When all required fields are collected, or the recruiter says they are done, call the finalize_session tool immediately.

REQUIRED FIELDS — collect ALL of these before calling finalize_session:
1. Job title
2. Company name
3. Location and work type (remote, onsite, or hybrid)
4. Employment type (full-time, part-time, contract, or internship)
5. Experience level and years of experience
6. Salary range and currency
7. Required skills (at least 3)
8. Job description or summary
9. Key responsibilities (at least 2)
10. Qualifications (at least 2)

OPTIONAL FIELDS — collect if the conversation naturally leads to them:
- Department
- Preferred skills
- Benefits
- Number of openings
- Application deadline

TOOL USAGE:
- Call record_* tools immediately after confirming each value. Do not batch tool calls to the end.
- After calling a tool, continue the conversation naturally. Do not narrate tool usage to the user.
- Do not say things like "I'm saving that now" or "Let me record that". Just confirm and move on.
- When calling finalize_session, say something like: "I have everything I need for the posting. You can review and submit the form whenever you are ready." Do not mention tools.

SPEECH RULES:
- Salary: Say "fifty to seventy thousand dollars per year" not "$50,000-$70,000/year".
- Dates: Say "December thirty-first" not "2024-12-31".
- Keep individual responses under 40 words when possible.
- Never use em-dashes, bullet symbols, asterisks, or markdown in spoken responses."""


# ── Agent class ───────────────────────────────────────────────────────────────

class JobPostingAgent(Agent):

    def __init__(self) -> None:
        super().__init__(instructions=AGENT_INSTRUCTIONS)

    # ── Lifecycle: called when agent enters the session ───────────────────────
    async def on_enter(self) -> None:
        """
        Called automatically by LiveKit Agents when this agent becomes active
        in the session. We use it to trigger the opening greeting.

        The greeting instructions here are intentionally separate from
        AGENT_INSTRUCTIONS so that the LLM generates a natural, unique
        greeting each time rather than reading a scripted line.
        """
        await self.session.generate_reply(
            instructions=(
                "Greet the recruiter warmly in one sentence. "
                "Then immediately ask: what job title are you hiring for? "
                "Keep the entire opening to two sentences maximum. "
                "Do not mention that you are an AI or voice assistant."
            )
        )

    # ── Internal helper: publish a field update to the frontend ──────────────
    async def _publish_field_update(
        self,
        context: RunContext[JobPostingData],
        field: str,
        value,
    ) -> None:
        """
        Publish a structured JSON message to the LiveKit room's DataChannel.
        The React frontend listens on topic "job_posting_updates" and uses
        these messages to update form fields in real time.

        field: must exactly match a key in JobPostingData and a form field
               name in the React frontend. Do not rename or alias.
        value: the new value for the field (str, int, list, or None).
        reliable=True: ensures delivery even on brief network fluctuations.
        """
        message = json.dumps({
            "type": "field_update",
            "field": field,
            "value": value,
        })
        try:
            room = context.session.room_io.room
            await room.local_participant.publish_data(
                payload=message.encode("utf-8"),
                reliable=True,
                topic="job_posting_updates",   # MUST match useDataChannel("job_posting_updates") in React
            )
            logger.debug(f"Published field_update | field={field} | value={value}")
        except Exception as e:
            # Log but do not raise — a failed DataChannel publish should not
            # crash the agent or interrupt the conversation.
            logger.error(f"Failed to publish field_update for field={field}: {e}")

    # ────────────────────────────────────────────────────────────────────────
    # Data collection tools
    # Each tool: (1) updates userdata, (2) publishes DataChannel update(s)
    # ────────────────────────────────────────────────────────────────────────

    @function_tool()
    async def record_job_title(
        self,
        context: RunContext[JobPostingData],
        job_title: str,
    ) -> None:
        """Call this tool to record the job title. Call it as soon as the recruiter tells you the job title or role name. job_title should be a clean title string, e.g. 'Senior Full Stack Engineer'."""
        context.userdata.job_title = job_title
        await self._publish_field_update(context, "job_title", job_title)

    @function_tool()
    async def record_company_name(
        self,
        context: RunContext[JobPostingData],
        company_name: str,
    ) -> None:
        """Call this tool to record the company name for this job posting. Call it as soon as the recruiter tells you the company name."""
        context.userdata.company_name = company_name
        await self._publish_field_update(context, "company_name", company_name)

    @function_tool()
    async def record_department(
        self,
        context: RunContext[JobPostingData],
        department: str,
    ) -> None:
        """Call this tool to record the department this role belongs to, e.g. Engineering, Product, Sales, Marketing. Only call this if the recruiter explicitly mentions a department."""
        context.userdata.department = department
        await self._publish_field_update(context, "department", department)

    @function_tool()
    async def record_location(
        self,
        context: RunContext[JobPostingData],
        location: str,
        work_type: str,
    ) -> None:
        """Call this tool to record the job location and work arrangement together. location: the city and country, e.g. 'Hyderabad, India', or the string 'Remote' if fully remote. work_type: must be exactly one of these three strings: 'remote', 'onsite', or 'hybrid'. Call this as soon as the recruiter tells you where the job is based or whether it is remote."""
        context.userdata.location = location
        context.userdata.work_type = work_type
        await self._publish_field_update(context, "location", location)
        await self._publish_field_update(context, "work_type", work_type)

    @function_tool()
    async def record_employment_type(
        self,
        context: RunContext[JobPostingData],
        employment_type: str,
    ) -> None:
        """Call this tool to record the employment type. employment_type must be exactly one of: 'full-time', 'part-time', 'contract', 'internship'. Map the recruiter's words to the correct value, e.g. 'permanent' maps to 'full-time'."""
        context.userdata.employment_type = employment_type
        await self._publish_field_update(context, "employment_type", employment_type)

    @function_tool()
    async def record_experience(
        self,
        context: RunContext[JobPostingData],
        experience_level: str,
        years_min: int,
        years_max: int,
    ) -> None:
        """Call this tool to record the experience requirements. experience_level must be exactly one of: 'entry', 'mid', 'senior', 'lead', 'executive'. years_min: minimum years required as an integer. years_max: maximum years preferred as an integer — use the same value as years_min if no range is given. If the recruiter says 'at least 5 years', set years_min=5, years_max=5."""
        context.userdata.experience_level = experience_level
        context.userdata.experience_years_min = years_min
        context.userdata.experience_years_max = years_max
        await self._publish_field_update(context, "experience_level", experience_level)
        await self._publish_field_update(context, "experience_years_min", years_min)
        await self._publish_field_update(context, "experience_years_max", years_max)

    @function_tool()
    async def record_salary(
        self,
        context: RunContext[JobPostingData],
        salary_min: int,
        salary_max: int,
        currency: str,
        period: str,
    ) -> None:
        """Call this tool to record the salary range. salary_min and salary_max are integers (no commas or symbols). currency is a currency code e.g. 'INR', 'USD', 'EUR', 'GBP'. period is either 'per year' or 'per month'. If the recruiter says the salary is confidential or not yet decided, call this tool with salary_min=0 and salary_max=0 and still record the currency and period if known."""
        context.userdata.salary_min = salary_min
        context.userdata.salary_max = salary_max
        context.userdata.salary_currency = currency
        context.userdata.salary_period = period
        await self._publish_field_update(context, "salary_min", salary_min)
        await self._publish_field_update(context, "salary_max", salary_max)
        await self._publish_field_update(context, "salary_currency", currency)
        await self._publish_field_update(context, "salary_period", period)

    @function_tool()
    async def record_required_skills(
        self,
        context: RunContext[JobPostingData],
        skills: list[str],
    ) -> None:
        """Call this tool to record the required (must-have) technical and non-technical skills for this role. skills is a list of skill name strings, e.g. ['Python', 'React', 'PostgreSQL', 'REST APIs']. This REPLACES any previously recorded required skills entirely — always pass the complete final list. Call this once after the recruiter has finished listing required skills."""
        context.userdata.skills_required = skills
        await self._publish_field_update(context, "skills_required", skills)

    @function_tool()
    async def record_preferred_skills(
        self,
        context: RunContext[JobPostingData],
        skills: list[str],
    ) -> None:
        """Call this tool to record the preferred (nice-to-have) skills for this role. skills is a list of skill name strings. This REPLACES any previously recorded preferred skills entirely. Only call this if the recruiter explicitly mentions preferred or bonus skills."""
        context.userdata.skills_preferred = skills
        await self._publish_field_update(context, "skills_preferred", skills)

    @function_tool()
    async def record_job_description(
        self,
        context: RunContext[JobPostingData],
        description: str,
    ) -> None:
        """Call this tool to record the overall job description or summary. description is a 2-4 sentence paragraph summarizing the role. Compose this from everything the recruiter has told you — do not ask them to dictate a full paragraph. Write it in second-person employer voice, e.g. 'We are looking for a senior engineer to lead...'."""
        context.userdata.job_description = description
        await self._publish_field_update(context, "job_description", description)

    @function_tool()
    async def record_responsibilities(
        self,
        context: RunContext[JobPostingData],
        responsibilities: list[str],
    ) -> None:
        """Call this tool to record the key responsibilities of the role. responsibilities is a list of strings, each describing one responsibility. Each string should start with an action verb, e.g. 'Lead the backend architecture design'. This REPLACES any previously recorded responsibilities entirely."""
        context.userdata.responsibilities = responsibilities
        await self._publish_field_update(context, "responsibilities", responsibilities)

    @function_tool()
    async def record_qualifications(
        self,
        context: RunContext[JobPostingData],
        qualifications: list[str],
    ) -> None:
        """Call this tool to record the required qualifications. qualifications is a list of strings, e.g. ["Bachelor's degree in Computer Science or related field", "5+ years of Python experience"]. This REPLACES any previously recorded qualifications entirely."""
        context.userdata.qualifications = qualifications
        await self._publish_field_update(context, "qualifications", qualifications)

    @function_tool()
    async def record_benefits(
        self,
        context: RunContext[JobPostingData],
        benefits: list[str],
    ) -> None:
        """Call this tool to record the benefits offered with this role. benefits is a list of strings, e.g. ['Health insurance', 'Remote work allowance', 'Stock options']. Only call this if the recruiter mentions benefits."""
        context.userdata.benefits = benefits
        await self._publish_field_update(context, "benefits", benefits)

    @function_tool()
    async def record_openings_and_deadline(
        self,
        context: RunContext[JobPostingData],
        number_of_openings: int,
        application_deadline: str | None,
    ) -> None:
        """Call this tool to record the number of open positions and the application deadline. number_of_openings is an integer — use 1 if the recruiter does not specify. application_deadline is a date string in ISO format 'YYYY-MM-DD', or None if not specified. Convert any spoken date (e.g. 'end of December') to the ISO format."""
        context.userdata.number_of_openings = number_of_openings
        context.userdata.application_deadline = application_deadline
        await self._publish_field_update(context, "number_of_openings", number_of_openings)
        await self._publish_field_update(context, "application_deadline", application_deadline)

    # ── Session finalization ──────────────────────────────────────────────────

    @function_tool()
    async def finalize_session(
        self,
        context: RunContext[JobPostingData],
    ) -> None:
        """Call this tool when ALL required fields have been collected and the recruiter confirms the information is correct, OR when the recruiter explicitly says they are done or want to stop. This ends the voice session. Do not call this tool until you have collected at least: job_title, company_name, location, work_type, employment_type, experience_level, salary details, required_skills, job_description, responsibilities, and qualifications."""
        logger.info(
            f"finalize_session called | session_id={context.userdata.session_id}"
        )

        # ── Step 1: Serialize collected data ─────────────────────────────────
        # asdict() converts the JobPostingData dataclass to a plain dict.
        # This is safe even if some optional fields are None — they will appear
        # as null in the JSON, which the frontend handles correctly.
        job_data_dict = asdict(context.userdata)

        # ── Step 2: Publish session_complete to the frontend via DataChannel ──
        # The frontend receives this and sets the form to its final state.
        # This message is published BEFORE the HTTP call to FastAPI so the
        # recruiter's UI updates immediately, even if the HTTP call is slow.
        complete_message = json.dumps({
            "type": "session_complete",
            "job_data": job_data_dict,
        })
        try:
            room = context.session.room_io.room
            await room.local_participant.publish_data(
                payload=complete_message.encode("utf-8"),
                reliable=True,
                topic="job_posting_updates",   # must match React's useDataChannel topic
            )
            logger.info("session_complete DataChannel message published.")
        except Exception as e:
            logger.error(f"Failed to publish session_complete message: {e}")
            # Continue — do not abort finalization if DataChannel publish fails.

        # ── Step 3: POST final data to FastAPI internal endpoint ──────────────
        # This is a server-side backup. The frontend already has the data from
        # the DataChannel message above.
        # Security: X-Internal-Token header must be present and must match
        # INTERNAL_API_SECRET — the FastAPI endpoint rejects requests without it.
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{INTERNAL_API_BASE_URL}/api/voice/end-session",
                    json={
                        "session_id": context.userdata.session_id,
                        "job_data": job_data_dict,
                        "conversation_transcript": [],
                    },
                    headers={
                        "Content-Type": "application/json",
                        "X-Internal-Token": INTERNAL_API_SECRET,  # CRITICAL — do not remove
                    },
                )
                if response.status_code == 200:
                    logger.info(
                        f"FastAPI end-session confirmed | session_id={context.userdata.session_id}"
                    )
                else:
                    logger.warning(
                        f"FastAPI end-session returned {response.status_code} "
                        f"for session_id={context.userdata.session_id}"
                    )
        except httpx.RequestError as e:
            # Log but do not crash — the frontend has the data from DataChannel.
            logger.error(
                f"Failed to POST to FastAPI end-session: {e}. "
                f"DataChannel message was already sent — recruiter's form data is safe."
            )

        # ── Step 4: Short delay, then disconnect ──────────────────────────────
        # The 2-second delay gives the DataChannel message time to deliver
        # to the frontend before the WebRTC connection closes.
        # Disconnecting immediately after publish_data can cause the message
        # to be dropped on slow connections.
        await asyncio.sleep(2)

        try:
            # In current LiveKit Agents SDK versions, RunContext exposes the
            # room through session.room_io and session teardown is managed via
            # AgentSession.shutdown().
            context.session.shutdown(drain=True)
            logger.info(
                f"Agent disconnected from room | session_id={context.userdata.session_id}"
            )
        except Exception as e:
            logger.error(f"Error disconnecting from room: {e}")