from app.agents.hr_agent import hr_agent
from app.agents.it_agent import it_agent
from app.agents.finance_agent import finance_agent

# Keys must EXACTLY match planner department strings: "HR", "IT", "Finance"
AGENT_REGISTRY = {
    "HR": hr_agent,
    "IT": it_agent,
    "Finance": finance_agent,
}