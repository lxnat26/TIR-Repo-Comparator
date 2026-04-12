from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from CoverageAssistant.backend.coverage_crew.tools.query_chromadb import QueryDBTool
from typing import List


@CrewBase
class CoverageCrew():
    """Coverage crew for comprehensive extracting, comparing, and classification"""

    agents: List[BaseAgent]
    tasks: List[Task]

    @agent
    def claim_extractor(self) -> Agent:
        return Agent(
            config=self.agents_config['claim_extractor'],
            verbose=True
        )
    
    @agent
    def claim_comparator(self) -> Agent:
        return Agent(
            config=self.agents_config['claim_comparator'],
            verbose=True,
            tools=[QueryDBTool()],
            max_iter=3
        )
    
    @agent 
    def claim_classifier(self) -> Agent:
        return Agent(
            config=self.agents_config['claim_classifier'],
            verbose=True
        )
    
    @task
    def claim_extractor_task(self) -> Task:
        return Task(
            config=self.tasks_config['claim_extractor_task']
        )
    
    @task
    def claim_comparator_task(self) -> Task:
        return Task(
            config=self.tasks_config['claim_comparator_task'],
            tools=[QueryDBTool()]
        )

    @task
    def claim_classifier_task(self) -> Task:
        return Task(
            config=self.tasks_config['claim_classifier_task']
        )
    
    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )